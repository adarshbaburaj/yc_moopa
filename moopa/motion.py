"""Fall detection from the band's raw accelerometer, computed on this laptop (nothing is uploaded).

A fall = free-fall  (total acceleration < FREEFALL_G for at least FREEFALL_MIN_S)
       -> impact    (a peak >= IMPACT_G within IMPACT_WINDOW_S of the free-fall starting)
       -> still     (acceleration steady near 1 g for STILL_S, after LANDING_S to settle)
How far the wrist turned (gravity direction before vs after) is reported as evidence.

Free-fall with no impact (e.g. the arm swinging) or movement afterwards (they got up) is
not a fall. Numbers are guesses tuned on the pretend band and a drop onto a cushion;
change them in .env, not here.
"""

import math
import os
from collections import deque


def _f(name, default):
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return float(default)


# LIVE_DEMO.md stage 1 (fast, sensitive). Tune from the TUNE lines printed for every candidate.
FREEFALL_G = _f("FALL_FREEFALL_G", 0.4)
FREEFALL_MIN_S = 0.08
IMPACT_G = _f("FALL_IMPACT_G", 2.5)
IMPACT_WINDOW_S = 1.5
LANDING_S = 1.0
STILL_S = _f("FALL_STILL_S", 3.0)
STILL_STD_G = _f("FALL_STILL_STD_G", 0.08)


def _mean_dir(samples):
    if not samples:
        return None
    x = sum(s[1] for s in samples) / len(samples)
    y = sum(s[2] for s in samples) / len(samples)
    z = sum(s[3] for s in samples) / len(samples)
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x / n, y / n, z / n)


def _angle(a, b):
    if not a or not b:
        return None
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
    return math.degrees(math.acos(dot))


class FallDetector:
    """feed() every sample (t in seconds, from the band's own clock). Calls on_fall(details)
    once per fall and on_note(text) for the steps in between (for the dashboard timeline)."""

    def __init__(self, on_fall, on_note=lambda text: None, on_raw=lambda text: None):
        self.on_fall = on_fall
        self.on_note = on_note
        self.on_raw = on_raw  # one TUNE line per candidate: the raw numbers, to set thresholds from data
        self.buf: deque = deque(maxlen=50 * 20)  # (t, ax, ay, az, |a|)
        self._reset()

    def _reset(self):
        self.phase = "idle"
        self.low_since = None
        self.ff_t = None
        self.impact_t = None
        self.peak = 0.0
        self.low = 9.9
        self.before = None

    def feed(self, t: float, ax: float, ay: float, az: float):
        mag = math.sqrt(ax * ax + ay * ay + az * az)
        self.buf.append((t, ax, ay, az, mag))
        if self.phase == "idle":
            if mag < FREEFALL_G:
                self.low_since = self.low_since if self.low_since is not None else t
                if t - self.low_since >= FREEFALL_MIN_S:
                    self.phase, self.ff_t = "falling", self.low_since
                    self.before = _mean_dir([s for s in self.buf if self.ff_t - 2.0 <= s[0] <= self.ff_t - 0.2])
                    self.on_note("Free-fall")
            else:
                self.low_since = None
        elif self.phase == "falling":
            if mag > self.peak:
                self.peak = mag
            if mag < self.low:
                self.low = mag
            if mag >= IMPACT_G:
                self.impact_t = t
            if t - self.ff_t > IMPACT_WINDOW_S:
                if self.impact_t is None:
                    self.on_raw(f"TUNE free-fall min {self.low:.2f} g, peak {self.peak:.2f} g "
                                f"(< impact {IMPACT_G} g) -> no fall")
                    self.on_note(f"Free-fall without an impact (peak {self.peak:.1f} g): not a fall")
                    self._reset()
                else:
                    self.phase = "landed"
                    self.on_note(f"Impact {self.peak:.1f} g, checking for stillness")
        elif self.phase == "landed":
            settle = self.impact_t + LANDING_S
            if t < settle + STILL_S:
                return
            after = [s for s in self.buf if s[0] >= settle]
            mags = [s[4] for s in after]
            mean = sum(mags) / len(mags)
            std = math.sqrt(sum((m - mean) ** 2 for m in mags) / len(mags))
            turn = _angle(self.before, _mean_dir(after))
            raw = (f"min {self.low:.2f} g, peak {self.peak:.2f} g, free-fall {int((self.impact_t - self.ff_t) * 1000)} ms, "
                   f"still-std {std:.3f} g (max {STILL_STD_G}), turn {turn if turn is None else round(turn)} deg")
            if std <= STILL_STD_G:
                details = {"peak_g": round(self.peak, 2), "min_g": round(self.low, 2),
                           "turn_deg": None if turn is None else round(turn),
                           "freefall_s": round(self.impact_t - self.ff_t, 2),
                           "freefall_ms": int((self.impact_t - self.ff_t) * 1000),
                           "still_s": STILL_S, "still_std_g": round(std, 3),
                           "series_10hz": self._series(t)}
                self.on_raw("TUNE " + raw + " -> FALL")
                self._reset()
                self.on_fall(details)
            else:
                self.on_raw("TUNE " + raw + " -> moving again, no fall")
                self.on_note(f"Moving after the impact (variation {std:.2f} g): not a fall")
                self._reset()

    def _series(self, now: float) -> list[float]:
        """The last 10 s of |a| at 10 Hz (bin means), for the Gemini check."""
        out = []
        for i in range(100):
            lo, hi = now - 10 + i * 0.1, now - 10 + (i + 1) * 0.1
            b = [s[4] for s in self.buf if lo <= s[0] < hi]
            out.append(round(sum(b) / len(b), 2) if b else None)
        return out


def describe(d: dict) -> str:
    turn = f", wrist turned {d['turn_deg']} degrees" if d.get("turn_deg") is not None else ""
    return f"Band: free-fall, {d['peak_g']} g impact{turn}, then still for {int(d['still_s'])} s"


def fall_motion(rate: int = 50) -> list[dict]:
    """A realistic fall for the pretend band: upright, free-fall, impact, bounce, lying still."""
    n = lambda s: int(s * rate)  # noqa: E731
    upright = [dict(az=1.0)] * n(0.6)
    falling = [dict(ax=0.03, ay=0.02, az=0.05)] * n(0.35)
    impact = [dict(ax=2.6, ay=0.4, az=-1.9), dict(ax=1.8, ay=-0.6, az=-0.9), dict(ax=1.3, ay=0.2, az=0.4)]
    bounce = [dict(ax=1.0 + (0.25 if i % 2 else -0.2), az=0.1) for i in range(n(0.3))]
    lying = [dict(ax=1.0, ay=0.02, az=0.03)] * n(8)
    return upright + falling + impact + bounce + lying
