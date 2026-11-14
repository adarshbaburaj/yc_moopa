"""Quick real-band check: connect to BAND_NUMBER from .env, show info, light green, test events.

Double-tap the band first (blinking blue = findable for ~60 s), then:
    .venv/bin/python tools/band_check.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vexo-open-kit" / "python"))
from dotenv import dotenv_values  # noqa: E402
from vexo_open.sync import Band  # noqa: E402

raw = (dotenv_values(ROOT / ".env").get("BAND_NUMBER") or "").strip()
if not raw.isdigit():
    sys.exit("Set BAND_NUMBER in .env (the number on the band's bag).")
n = int(raw)
print(f"Connecting to Vexo-HACK-{n:02d}... (macOS may ask to allow Bluetooth: click Allow)")
t = time.time()
band = Band.connect(n)
print(f"Connected in {time.time() - t:.1f}s: {band.name}")
band.set_led("#00ff00")
import os
thr = float(os.getenv("BAND_TAP_THRESHOLD") or dotenv_values(ROOT / ".env").get("BAND_TAP_THRESHOLD") or 0.5)
seen = []
band.on("event", lambda e: (seen.append(e.kind), print(f"  event: {e.kind}", flush=True)))
band.configure(events=True)
band.set_events(kinds=["tap", "double-tap", "free-fall", "tilt", "motion"], tap_threshold=thr)
print(f"Light is green. Tap sensitivity {thr} g (lower = more sensitive).")
print("Now tap, then double-tap the band firmly with a fingertip (20 s)...")
band.wait(20)
print("Events seen:", seen or "none")
band.disconnect()
print("OK - the band works. Run Moopa with:  .venv/bin/python run.py --band real --no-camera")
