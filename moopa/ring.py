"""COLMI R02 ring: heart rate + SpO2 into state.vitals.

  RingLink(mode="real")  scans for the ring over BLE (or RING_ADDRESS in .env), reads real-time
                         heart rate and SpO2 every RING_EVERY_S seconds. source = "ring".
  RingLink(mode="sim")   plausible numbers, source = "simulated". Labelled SIMULATED everywhere.

If the real ring can't be found or drops, it falls back to sim and says so in state, so the
dashboard and the agent never present simulated numbers as real.
"""

import asyncio
import os
import random
import statistics
import threading
import time

from moopa import console, state

EVERY_S = float(os.getenv("RING_EVERY_S", "30"))
NAMES = ("R02", "R03", "R06", "COLMI", "TR-R02")


def _set(hr, spo2, source):
    state.merge("vitals", {"heart_rate": hr, "spo2": spo2, "source": source, "ts": time.time()})


class RingLink:
    def __init__(self, mode: str = "sim"):
        self.mode = mode
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._thread, name="ring", daemon=True).start()
        return self

    def stop(self):
        self._stop.set()

    def _thread(self):
        if self.mode == "real":
            try:
                asyncio.run(self._real())
            except Exception as e:
                console.log(f"[ring] real ring failed: {e!r}")
            if self._stop.is_set():
                return
            state.emit("system", "Ring not reachable: showing SIMULATED vitals")
        self._sim()

    # ---------- simulated ----------
    def _sim(self):
        state.update("devices.ring", "sim")
        hr, spo2 = 72.0, 97.0
        while not self._stop.is_set():
            hr = min(84, max(62, hr + random.uniform(-2, 2)))
            spo2 = min(99, max(95, spo2 + random.uniform(-0.5, 0.5)))
            _set(round(hr), round(spo2), "simulated")
            self._stop.wait(5)

    # ---------- real COLMI ring ----------
    async def _find(self):
        addr = os.getenv("RING_ADDRESS", "").strip()
        if addr:
            return addr
        from bleak import BleakScanner

        state.update("devices.ring", "scanning")
        for _ in range(3):
            for d in await BleakScanner.discover(timeout=6):
                if d.name and d.name.upper().startswith(NAMES):
                    console.log(f"[ring] found {d.name} {d.address}")
                    return d.address
        return None

    async def _real(self):
        from colmi_r02_client.client import Client

        addr = await self._find()
        if not addr:
            raise RuntimeError("no COLMI ring found (is it charged and not paired to the phone app?)")
        while not self._stop.is_set():
            state.update("devices.ring", "connecting")
            async with Client(addr) as ring:
                state.update("devices.ring", "on")
                state.emit("system", "Ring connected: live heart rate and SpO2")
                fails = 0
                while not self._stop.is_set():
                    hr = await ring.get_realtime_heart_rate()
                    spo2 = await ring.get_realtime_spo2()
                    hr_v = round(statistics.median(hr)) if hr else None
                    sp_v = round(statistics.median(spo2)) if spo2 else None
                    if hr_v:
                        _set(hr_v, sp_v, "ring")
                        state.emit("vitals", f"Ring: heart rate {hr_v} bpm"
                                             + (f", SpO2 {sp_v}%" if sp_v else ""), source="ring")
                        fails = 0
                    else:
                        fails += 1
                        if fails >= 3:
                            raise RuntimeError("ring gives no readings (is it on a finger?)")
                    await asyncio.sleep(EVERY_S)
