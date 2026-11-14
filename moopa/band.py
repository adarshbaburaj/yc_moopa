"""Vexo band: double-tap wakes the agent, free-fall + stillness = fall, activity -> today's
summary, and (with --mic band) the band's microphone feeds the agent while it is awake.

Kit rules followed: handlers only record (into an inbox); the LED is set only while the
mic is off; the band number comes only from BAND_NUMBER in .env.
"""

import os
import queue
import sys
import threading
import time
from pathlib import Path

from moopa import state

KIT = Path(__file__).resolve().parent.parent / "vexo-open-kit" / "python"
sys.path.insert(0, str(KIT))

LANDING_S = 1.0   # movement in the first second after free-fall is the landing
STILL_S = 5.0     # still this long after landing = a fall
RESULT_LIGHT_S = 6.0
LIGHTS = {"idle": ("#003300", "breathe", 4000), "listen": ("#ffffff", "flash", 250),
          "done": ("#00ff00", "solid", 1000), "waiting": ("#ff8800", "blink", 600),
          "failed": ("#ff0000", "solid", 1000), "fall": ("#ff8800", "blink", 300),
          "alert": ("#ff0000", "flash", 300)}


def band_number() -> int | None:
    raw = os.getenv("BAND_NUMBER", "").strip()
    return int(raw) if raw.isdigit() and 1 <= int(raw) <= 999 else None


class BandLink:
    def __init__(self, agent, sim: bool, use_band_mic: bool):
        self.agent = agent
        self.sim = sim
        self.use_mic = use_band_mic
        self.band = None
        self.inbox: queue.Queue = queue.Queue(maxsize=2000)
        self.audio: queue.Queue = queue.Queue(maxsize=400)
        self.double_tap_hooks = []  # callables() -> bool; True = consumed (fall cancel uses this)
        self.fall_hooks = []        # callables(source)
        self._mic_on = False
        self._decoder = None
        self._fall_at = None
        self._first_steps = None
        self._last_activity = None
        self._wake_event_idx = 0
        self._result_until = 0.0

    # ---- public, thread-safe
    def sim_double_tap(self):
        if self.band and self.sim:
            self.band.transport.tap("double-tap")

    def sim_fall(self):
        if self.band and self.sim:
            self.band.transport.tap("free-fall")
            self.band.transport.set_activity("still")

    def light(self, name: str):
        """Only while the mic is off (the band refuses LED commands otherwise)."""
        if not self.band or self._mic_on:
            return
        colour, pattern, period = LIGHTS[name]
        try:
            self.band.set_led(colour, pattern=pattern, period=period)
        except Exception as e:  # not-connected while reconnecting, etc.: the demo goes on
            print(f"[band] light {name}: {e}")

    # ---- thread
    def start(self):
        threading.Thread(target=self._run, daemon=True, name="band").start()

    def _connect(self, number: int):
        from vexo_open.sync import Band

        if self.sim:
            from vexo_open.transports.sim import SimTransport

            return Band.connect(number, SimTransport(number, auto_tap=False))
        return Band.connect(number, auto_reconnect=True)

    def _run(self):
        number = band_number()
        if number is None:
            print("[band] BAND_NUMBER is not set in .env (the number on the band's bag). Running without the band.")
            state.update("devices.band", "off")
            return
        try:
            print(f"[band] connecting to Vexo-HACK-{number:02d}{' (pretend band)' if self.sim else ''}... "
                  f"{'' if self.sim else 'double-tap the band first'}")
            self.band = self._connect(number)
        except Exception as e:
            print(f"[band] could not connect: {e}")
            state.update("devices.band", "off")
            return
        b = self.band
        state.update("devices.band", "sim" if self.sim else "on")
        state.emit("system", f"Band connected: {b.name}{' (pretend)' if self.sim else ''}")
        put = lambda item: self.inbox.put_nowait(item) if not self.inbox.full() else None  # noqa: E731
        b.on("double-tap", lambda e: put(("double-tap", None)))
        b.on("free-fall", lambda e: put(("free-fall", None)))
        b.on("motion-start", lambda e: put(("moved", None)))
        b.on("activity", lambda e: put(("activity", (e.steps, e.state))))
        b.on("reconnecting", lambda e: put(("link", "lost")))
        b.on("reconnected", lambda e: put(("link", "back")))
        b.on("audio", lambda a: self.audio.put_nowait(a) if not self.audio.full() else None)
        b.configure(events=True, activity=True, battery=True)
        if self.use_mic:
            from vexo_open.audio import PcmDecoder

            print("[band] preparing the audio decoder (a few seconds, once)...")
            self._decoder = PcmDecoder()
            state.update("devices.mic", "band")
        self.light("idle")
        while True:
            try:
                self._tick()
            except Exception as e:
                print(f"[band] loop error: {e}")
                time.sleep(0.5)

    def _tick(self):
        time.sleep(0.03)
        now = time.time()
        # 1. microphone packets -> agent (decoded here, never in a handler)
        while not self.audio.empty():
            pkt = self.audio.get_nowait()
            if self._decoder and self._mic_on:
                pcm = self._decoder.feed(pkt)
                if pcm:
                    self.agent.feed_audio(bytes(pcm))
        # 2. what the band reported
        while not self.inbox.empty():
            kind, data = self.inbox.get_nowait()
            if kind == "double-tap":
                state.emit("band", "Double-tap")
                if any(h() for h in list(self.double_tap_hooks)):
                    continue
                self._wake()
            elif kind == "free-fall":
                state.emit("band", "Free-fall detected, checking for stillness")
                self._fall_at = now
            elif kind == "moved":
                if self._fall_at and now - self._fall_at > LANDING_S:
                    state.emit("band", "Moving again after free-fall: no fall")
                    self._fall_at = None
            elif kind == "activity":
                self._activity(now, *data)
            elif kind == "link":
                state.emit("system", f"Band link {data}")
                if data == "back":
                    self._mic_on = False
                    self.light("idle")
        # 3. fall = free-fall then still for STILL_S
        if self._fall_at and now - self._fall_at >= LANDING_S + STILL_S:
            self._fall_at = None
            for h in list(self.fall_hooks):
                h("band")
        # 4. mic follows the agent's awake window (band mic mode only)
        awake = state.get("awake")
        if self.use_mic and awake and not self._mic_on:
            self.light("listen")
            time.sleep(0.25)
            self.band.configure(audio=True)  # light goes solid blue by itself
            self._mic_on = True
        elif self.use_mic and not awake and self._mic_on:
            self.band.configure(audio=False)
            self._mic_on = False
            self._show_result()
        elif not self.use_mic and not awake and self._wake_event_idx and not self._result_until:
            self._show_result()
        if self._result_until and now > self._result_until:
            self._result_until = 0.0
            self._wake_event_idx = 0
            self.light("alert" if state.get("status") == "ALERT" else "idle")

    def _wake(self):
        self._wake_event_idx = len(state.snapshot()["events"]) or 1
        self._wake_ts = time.time()
        if not self.use_mic:
            self.light("listen")
        self.agent.wake()

    def _show_result(self):
        since = getattr(self, "_wake_ts", 0)
        evs = [e for e in state.snapshot()["events"] if e["ts"] >= since]
        pend = state.get("pending_confirmation")
        texts = " ".join(e["text"].lower() for e in evs if e["kind"] == "action")
        if pend and pend.get("ts", 0) >= since:
            name = "waiting"
        elif any(w in texts for w in ("failed", "blocked", "gave up", "error", "did not")):
            name = "failed"
        else:
            name = "done"
        if state.get("status") == "ALERT":
            name = "alert"
        self.light(name)
        self._result_until = time.time() + RESULT_LIGHT_S

    def _activity(self, now, steps, act_state):
        if self._first_steps is None:
            self._first_steps = steps
        dt = min(now - self._last_activity, 5.0) if self._last_activity else 0.0
        self._last_activity = now
        a = state.get("activity")
        merged = {"steps": max(0, steps - self._first_steps), "current": act_state}
        if act_state == "still":
            merged["still_s"] = a["still_s"] + dt
        else:
            merged["active_s"] = a["active_s"] + dt
            if self._fall_at and now - self._fall_at > LANDING_S:
                state.emit("band", "Moving again after free-fall: no fall")
                self._fall_at = None
        state.merge("activity", merged)
