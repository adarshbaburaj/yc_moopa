"""Fall response (LIVE_DEMO.md): band rule fires -> Gemini checks the motion (<= 3 s, fails safe)
-> "Are you okay? Are you all right?" -> listen 10 s -> Gemini judges the reply -> decide in code.

Truth table (decided here, not by a model):
  Gemini motion check: p(fall) < 0.5           -> log it, no check-in   (timeout/error -> check-in anyway)
  reply ok, confidence >= 0.7                  -> "Okay, I'm glad..." and back to idle
  reply unclear, or ok below 0.7               -> ask once more ("Are you hurt? Say yes or no.")
  needs_help / no_response / unclear twice     -> "I'm calling your family now." + call + dashboard red
  double-tap on the band                       -> "I'm fine": cancel
  Gemini unreachable                           -> TypeSafe System One, then keywords (a failure is never "fine")
"""

import json
import os
import re
import threading
import time
import urllib.request

from moopa import console  # noqa: E402
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


LEAN = 0.5


CONSENT_Q = {
    "agrees": {
        "type": "noul",
        "instructions": "Does the person in `reply` clearly agree to go ahead with what was asked in `question`?",
        "criteria": {"true": "They say yes, go ahead, okay do it, or similar, without doubt",
                     "false": "They say no, wait, not now, ask a question back, or sound unsure"},
    },
}
_YES = re.compile(r"\b(yes|yeah|yep|sure|go ahead|ok(ay)?|please do|do it)\b", re.I)
_NOT = re.compile(r"\b(no|not|don'?t|wait|stop|maybe|later|why|how much)\b", re.I)


def judge_consent(question: str, reply: str) -> tuple[float, str]:
    """-> (p_agrees, source). Code decides with YES (0.7); a failed call is never read as yes."""
    key = os.getenv("TYPESAFE_API_KEY", "").strip()
    if key:
        body = {"model": os.getenv("TYPESAFE_MODEL", "jev-latest"),
                "state": {"question": question, "reply": reply}, "questions": CONSENT_Q}
        req = urllib.request.Request(JEV_URL, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=6) as r:
                return float(json.load(r)["answers"]["agrees"]["noul"]), "jev"
        except Exception as e:
            state.emit("system", f"System One unavailable ({str(e)[:80]}), using keywords")
    return (0.9 if _YES.search(reply) and not _NOT.search(reply) else 0.1), "keywords"


def decide(p_ok: float, p_help: float) -> str:
    if p_help >= YES:
        return "alert"
    if p_ok < NO and p_help >= LEAN:  # clearly not "I'm okay", and leaning towards needing help
        return "alert"
    if p_ok >= YES and p_help < NO:
        return "cancel"
    return "wait"


# ---- LIVE_DEMO.md wording and limits, all in one place
CHECK_Q = "Are you okay? Are you all right?"
RETRY_Q = "I didn't catch that. Are you hurt? Say yes or no."
OK_LINE = "Okay, I'm glad. Tap twice if you need me."
CALL_LINE = "I'm calling your family now."
VERIFY_TIMEOUT_S = 3.0
JUDGE_TIMEOUT_S = 5.0
SETTLE_S = 1.2        # judge this long after the last words, so "I'm... fine" is one answer
OK_MIN = 0.7
FALL_MIN = 0.5

_genai_client = None


def _gemini_json(prompt: str, timeout: float) -> dict:
    """One JSON answer from Gemini (Vertex if configured), or raise on timeout/error."""
    import concurrent.futures

    def call():
        global _genai_client
        from google import genai
        from google.genai import types
        if _genai_client is None:  # keep one client: a dropped client closes its connection
            vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes")
            _genai_client = genai.Client() if vertex else genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        # measured on our Vertex project: gemini-3-flash-preview + minimal thinking ~1 s, gemini-4-hydrogen ~2.8 s
        r = _genai_client.models.generate_content(
            model=os.getenv("FALL_GEMINI_MODEL", "gemini-3-flash-preview"), contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0,
                thinking_config=types.ThinkingConfig(thinking_level=os.getenv("FALL_GEMINI_THINKING", "minimal"))))
        m = re.search(r"\{.*\}", r.text or "", re.S)
        return json.loads(m.group(0)) if m else {}

    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        return ex.submit(call).result(timeout=timeout)
    finally:
        ex.shutdown(wait=False)


def _quiet(fn, *a):
    try:
        fn(*a)
    except Exception:
        pass


def verify_motion(details: dict) -> tuple[float | None, str]:
    """Stage 2 -> (p_fall or None if Gemini failed, reason)."""
    feats = {k: details.get(k) for k in ("min_g", "peak_g", "freefall_ms", "turn_deg", "still_std_g", "still_s")}
    prompt = ("A wrist band's accelerometer rule flagged a possible fall of an elderly wearer. Judge from these "
              "features whether it was a real fall (or the band itself being dropped, which we treat the same) "
              "rather than normal movement like waving an arm, putting the band down or sitting down hard.\n"
              f"features: {json.dumps(feats)}\n"
              f"|a| in g over the last 10 s at 10 Hz (oldest first, null = no sample): {json.dumps(details.get('series_10hz'))}\n"
              'Answer only JSON: {"fall": true|false, "confidence": 0..1, "reason": "short"}')
    try:
        j = _gemini_json(prompt, VERIFY_TIMEOUT_S)
        c = float(j.get("confidence", 0.5))
        return (c if j.get("fall") else 1 - c), str(j.get("reason", ""))[:140]
    except Exception as e:
        return None, f"Gemini check failed ({type(e).__name__}), checking in anyway"


def judge_checkin(question: str, reply: str) -> tuple[str, float, str, str]:
    """Stage 3 -> (status ok|needs_help|unclear|no_response, confidence, reason, source)."""
    if not reply.strip():
        return "no_response", 1.0, "nothing heard", "code"
    prompt = ("The speaker is an elderly person who may have just fallen. Their wristband assistant asked: "
              f'"{question}". Speech may be faint, slurred, partial or mis-transcribed: judge the meaning, not the '
              'exact words. "I\'m fine", "yeah yeah I\'m okay" -> ok. "I can\'t get up", "help", "my hip", groaning '
              'words, "call my son" -> needs_help. If the question was "Are you hurt? Say yes or no", then "yes" means '
              "needs_help and \"no\" means ok. Garbled or contradictory -> unclear. Empty -> no_response. "
              "If in doubt, prefer needs_help over ok.\n"
              f"transcript: {json.dumps(reply)}\n"
              'Answer only JSON: {"status": "ok"|"needs_help"|"unclear"|"no_response", "confidence": 0..1, "reason": "short"}')
    try:
        j = _gemini_json(prompt, JUDGE_TIMEOUT_S)
        st = j.get("status")
        if st in ("ok", "needs_help", "unclear", "no_response"):
            return st, float(j.get("confidence", 0.5)), str(j.get("reason", ""))[:140], "gemini"
    except Exception as e:
        state.emit("system", f"Gemini unavailable for the check-in ({type(e).__name__}), using System One")
    if question == RETRY_Q and re.fullmatch(r"\W*(yes|yeah|yep)\W*", reply, re.I):
        return "needs_help", 0.9, "said yes to being hurt", "keywords"
    if question == RETRY_Q and re.fullmatch(r"\W*(no|nope|no,? i'?m (fine|okay|ok))\W*", reply, re.I):
        return "ok", 0.8, "said no to being hurt", "keywords"
    p_ok, p_help, src = judge_reply(reply)
    v = decide(p_ok, p_help)
    st = {"alert": "needs_help", "cancel": "ok"}.get(v, "unclear")
    return st, max(p_ok, p_help), f"okay {p_ok:.2f}, needs help {p_help:.2f}", src


class FallResponder:
    def __init__(self, agent):
        self.agent = agent
        self.lock = threading.RLock()
        self.checking = False
        self.verifying = False
        self.judging = False
        self.attempt = 1
        self.question = CHECK_Q
        self.heard: list[str] = []
        self.last_heard = 0.0
        self.deadline = 0.0
        self.sources: dict[str, float] = {}
        self.description = None
        threading.Thread(target=self._timer, daemon=True, name="fall-timer").start()
        # warm Gemini now: the first call pays for login + connection, and a fall can't wait for that
        threading.Thread(target=lambda: _quiet(_gemini_json, 'Answer only JSON {"ok": true}', 15),
                         daemon=True, name="gemini-warm").start()

    # ---- inputs
    def trigger(self, source: str, description: str | None = None, details: dict | None = None):
        with self.lock:
            now = time.time()
            self.sources = {s: t for s, t in self.sources.items() if now - t < CONFIRM_WINDOW_S}
            self.sources[source] = now
            if description:
                self.description = description
            if state.get("status") == "ALERT" or self.checking or self.verifying:
                return
            self.verifying = bool(details)
        if details:
            state.emit("fall", f"Possible fall ({description or source}). Checking the motion with Gemini.", source=source)
            threading.Thread(target=self._verify, args=(source, details), daemon=True).start()
        else:
            self._start_check(source)

    def _verify(self, source: str, details: dict):
        t0 = time.time()
        p_fall, reason = verify_motion(details)
        ms = int((time.time() - t0) * 1000)
        with self.lock:
            self.verifying = False
        if p_fall is None:
            state.emit("judge", f"Gemini motion check: {reason} [{ms} ms]", source="gemini")
            self._start_check(source)
        elif p_fall >= FALL_MIN:
            state.emit("judge", f"Gemini motion check: fall {p_fall:.2f} ({reason}) [{ms} ms] -> check in",
                       p_fall=p_fall, source="gemini")
            self._start_check(source)
        else:
            state.emit("judge", f"Gemini motion check: not a fall, fall {p_fall:.2f} ({reason}) [{ms} ms] -> no check-in",
                       p_fall=p_fall, source="gemini")

    def _start_check(self, source: str):
        with self.lock:
            if self.checking or state.get("status") == "ALERT":
                return
            self.checking, self.attempt, self.question = True, 1, CHECK_Q
            self.heard, self.judging = [], False
            self.deadline = time.time() + SPEAK_S + REPLY_S
        a = state.get("activity")
        state.merge("activity", {"falls": a["falls"] + 1})
        state.update("status", "CHECKING")
        state.emit("fall", f"Possible fall ({source}). Asking: {CHECK_Q}", source=source)
        self.agent.wake(greet=CHECK_Q, remember=True)

    def on_transcript(self, text: str) -> bool:
        """While checking in, the reply belongs to this check (the chat agent doesn't answer it)."""
        with self.lock:
            if not self.checking:
                return False
            self.heard.append(text.strip())
            self.last_heard = time.time()
        return True

    def on_double_tap(self) -> bool:
        with self.lock:
            if self.checking or state.get("status") == "ALERT":
                self._cancel("Double-tap: wearer says they are okay")
                return True
        return False

    # ---- decisions
    def _judge(self, text: str):
        st, conf, reason, src = judge_checkin(self.question, text)
        state.emit("judge", f"Check-in \"{text}\" -> {st} {conf:.2f} ({reason}) [{src}]",
                   status=st, confidence=conf, source=src)
        with self.lock:
            self.judging = False
            if not self.checking:
                return
            retry = (st == "unclear" or (st == "ok" and conf < OK_MIN)) and self.attempt == 1
            if retry:
                self.attempt, self.question = 2, RETRY_Q
                self.deadline = time.time() + SPEAK_S + REPLY_S
        if st == "ok" and conf >= OK_MIN:
            self.agent.say(OK_LINE)
            self._cancel("Fall: the person said they're fine")
        elif retry:
            state.emit("fall", "Reply unclear: asking once more")
            self.agent.say(RETRY_Q)
        else:
            why = {"needs_help": "Said they need help", "no_response": "No answer"}.get(st, "Still unclear after asking twice")
            self.alert(f"{why} after a fall: \"{text}\" ({reason})")

    def _cancel(self, why: str):
        with self.lock:
            self.checking = False
            self.verifying = False
            self.sources.clear()
            self.description = None
        state.update("status", "OK")
        state.update("alert", None)
        state.emit("fall", f"Cancelled: {why}")

    def _timer(self):
        while True:
            time.sleep(0.2)
            now = time.time()
            judge = None
            with self.lock:
                if not self.checking:
                    continue
                speaking = self.agent.gate.bot_speaking
                if self.heard and not self.judging and now - self.last_heard >= SETTLE_S:
                    judge, self.heard, self.judging = " ".join(self.heard), [], True
                due = (not self.heard and not self.judging and not speaking and now > self.deadline)
            # keep the mic open for the whole reply window (the normal awake window is shorter)
            self.agent.gate.awake_until = max(self.agent.gate.awake_until, time.monotonic() + 1.0)
            if judge is not None:
                threading.Thread(target=self._judge, args=(judge,), daemon=True).start()
            elif due:
                state.emit("judge", "Check-in: no_response (nothing heard for 10 s)", status="no_response", source="code")
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
        self.agent.say(CALL_LINE)
        self.agent.stop_listening("Mic off: calling family")  # the call's audio must not reach the agent

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
