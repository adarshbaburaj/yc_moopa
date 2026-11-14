"""Fall response: ask "Are you okay?", judge the reply with TypeSafe System One (Jev),
decide in code. No answer within REPLY_S -> alert family (call) + dashboard goes red.

Truth table (decided here, not by a model):
  asks_help >= 0.7                      -> ALERT now
  says_ok >= 0.7 and asks_help < 0.3    -> cancel (they're fine)
  anything else (unclear)               -> keep waiting; at the deadline -> ALERT
  double-tap on the band                -> cancel
  Jev unreachable                       -> keyword fallback (never read a failure as "fine")
"""

import json
import os
import re
import threading
import time
import urllib.request

from moopa import phone, state

REPLY_S = 10.0       # after the question has been spoken
SPEAK_S = 3.0        # rough time to say the question
CONFIRM_WINDOW_S = 30.0
YES, NO = 0.7, 0.3

# ---- System One questions: all wording in one place
JEV_URL = "https://api.typesafe.ai/v1/systemone"
QUESTIONS = {
    "says_ok": {
        "type": "noul",
        "instructions": "Does the person in `reply` say they are okay?",
        "criteria": {"true": "They say they are fine, okay, not hurt, or that they don't need anything",
                     "false": "They say they are hurt, in pain or can't get up, or they don't answer the question"},
    },
    "asks_help": {
        "type": "noul",
        "instructions": "Does the person in `reply` ask for help or say they are hurt?",
        "criteria": {"true": "They ask for help, or say they are hurt, in pain, dizzy, or cannot get up",
                     "false": "They say they are fine and need nothing"},
    },
}
_HELP = re.compile(r"\b(help\w*|hurt\w*|pain\w*|ache\w*|aching|can'?t (get up|move|stand)|cannot (get up|move|stand)|"
                   r"dizzy|bleed\w*|ambulance|broke\w*|fell|no+)\b", re.I)
_OK = re.compile(r"\b(i'?m (fine|ok|okay|alright|good)|i am (fine|ok|okay|alright)|fine|okay|all right|not hurt)\b", re.I)


def judge_reply(reply: str) -> tuple[float, float, str]:
    """-> (p_says_ok, p_asks_help, source). Source is 'jev' or 'keywords'."""
    key = os.getenv("TYPESAFE_API_KEY", "").strip()
    if key:
        body = {"model": os.getenv("TYPESAFE_MODEL", "jev-latest"),
                "state": {"situation": "An older adult's wristband detected a possible fall. "
                                       "The assistant asked: \"I think you fell. Are you okay?\"",
                          "reply": reply},
                "questions": QUESTIONS}
        req = urllib.request.Request(JEV_URL, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=6) as r:
                ans = json.load(r)["answers"]
            return float(ans["says_ok"]["noul"]), float(ans["asks_help"]["noul"]), "jev"
        except Exception as e:
            state.emit("system", f"System One unavailable ({str(e)[:80]}), using keywords")
    help_ = bool(_HELP.search(reply))
    ok = bool(_OK.search(reply)) and not help_
    return (0.9 if ok else 0.1), (0.9 if help_ else 0.1), "keywords"


def decide(p_ok: float, p_help: float) -> str:
    if p_help >= YES:
        return "alert"
    if p_ok >= YES and p_help < NO:
        return "cancel"
    return "wait"


class FallResponder:
    def __init__(self, agent):
        self.agent = agent
        self.lock = threading.RLock()
        self.checking = False
        self.deadline = 0.0
        self.sources: dict[str, float] = {}
        self.description = None
        threading.Thread(target=self._timer, daemon=True, name="fall-timer").start()

    # ---- inputs
    def trigger(self, source: str, description: str | None = None):
        with self.lock:
            now = time.time()
            self.sources = {s: t for s, t in self.sources.items() if now - t < CONFIRM_WINDOW_S}
            self.sources[source] = now
            if description:
                self.description = description
            confirmed = len(self.sources) >= 2
            if state.get("status") == "ALERT":
                if confirmed:
                    a = dict(state.get("alert") or {})
                    a.update(confirmed=True, sources=sorted(self.sources), description=self.description)
                    state.update("alert", a)
                    state.emit("fall", f"Fall confirmed by {' + '.join(sorted(self.sources))}")
                return
            if self.checking:
                if confirmed:
                    state.emit("fall", f"Fall confirmed by {' + '.join(sorted(self.sources))}")
                return
            self.checking = True
            self.deadline = now + SPEAK_S + REPLY_S
        a = state.get("activity")
        state.merge("activity", {"falls": a["falls"] + 1})
        state.update("status", "CHECKING")
        state.emit("fall", f"Possible fall ({source}). Asking if they are okay.", source=source)
        self.agent.wake(greet="I think you fell. Are you okay?", remember=True)

    def on_transcript(self, text: str):
        with self.lock:
            if not self.checking:
                return
        threading.Thread(target=self._judge, args=(text,), daemon=True).start()

    def on_double_tap(self) -> bool:
        with self.lock:
            if self.checking or state.get("status") == "ALERT":
                self._cancel("Double-tap: wearer says they are okay")
                return True
        return False

    # ---- decisions
    def _judge(self, text: str):
        p_ok, p_help, src = judge_reply(text)
        verdict = decide(p_ok, p_help)
        state.emit("judge", f"\"{text}\" -> okay {p_ok:.2f}, needs help {p_help:.2f} ({src}) -> {verdict}",
                   p_ok=p_ok, p_help=p_help, source=src, verdict=verdict)
        if verdict == "alert":
            self.alert("Asked for help after a fall: " + text)
        elif verdict == "cancel":
            self._cancel("Said they are okay")

    def _cancel(self, why: str):
        with self.lock:
            self.checking = False
            self.sources.clear()
            self.description = None
        state.update("status", "OK")
        state.update("alert", None)
        state.emit("fall", f"Cancelled: {why}")

    def _timer(self):
        while True:
            time.sleep(0.2)
            with self.lock:
                due = self.checking and time.time() > self.deadline and not self.agent.gate.bot_speaking
            if due:
                self.alert("No answer for 10 seconds after a fall")

    def alert(self, reason: str) -> str:
        """Idempotent. Marks the alert, tells the elder, calls the first contact."""
        with self.lock:
            if state.get("status") == "ALERT":
                return "Family has already been alerted."
            self.checking = False
            confirmed = len(self.sources) >= 2
            info = {"reason": reason, "confirmed": confirmed, "sources": sorted(self.sources),
                    "description": self.description, "ts": time.time()}
        state.update("status", "ALERT")
        state.update("alert", info)
        state.emit("alert", f"ALERT: {reason}{' (confirmed by band + camera)' if confirmed else ''}")
        hit = phone.find_contact("grandson") or next(iter(phone.contacts().items()), None)
        if not hit:
            self.agent.say("I could not find anyone to call. I've marked an alert.")
            return "Alert marked, but there is no contact to call."
        who, num = hit
        self.agent.say(f"I'm calling your {who} now. Stay where you are.")

        def call():
            try:
                if os.getenv("CALL_VIA", "whatsapp") == "whatsapp":
                    phone.video_call(num, who)
                else:
                    phone.call_number(num, who)
            except Exception as e:
                state.emit("action", f"Alert call failed: {e}")

        threading.Thread(target=call, daemon=True).start()
        return f"Alert raised and calling {who}."

    def reset(self):
        self._cancel("Reset from the dashboard")
