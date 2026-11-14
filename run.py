"""Start Moopa. Every part can run without the others.

  python run.py                        sim band, Mac mic, sim ring, camera on, real phone
  python run.py --no-phone --no-camera print phone actions instead of doing them
  python run.py --band real --mic band real band (number from BAND_NUMBER in .env)

Keys in the terminal: SPACE = wake the agent (like a band double-tap),
f = pretend fall, c = cancel alert, q = quit.
"""

import argparse
import asyncio
import os
import sys
import termios
import threading
import tty
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from moopa import phone, server, state  # noqa: E402


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", choices=["real", "sim", "off"], default="sim",
                    help="real = the band numbered BAND_NUMBER in .env")
    ap.add_argument("--mic", choices=["band", "mac"], default="mac")
    ap.add_argument("--ring", choices=["real", "sim", "off"], default="sim")
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--no-phone", action="store_true", help="print phone actions instead of doing them")
    ap.add_argument("--port", type=int, default=8765)
    return ap.parse_args()


def keyboard(agent, extra: dict, stop: threading.Event):
    """Single-key commands without Enter. Runs in a thread."""
    if not sys.stdin.isatty():
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not stop.is_set():
            ch = sys.stdin.read(1)
            if ch == " ":
                state.emit("system", "Wake (space bar)")
                agent.wake()
            elif ch in extra:
                extra[ch]()
            elif ch == "q":
                stop.set()
                os.kill(os.getpid(), 2)
                return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


async def main():
    args = parse()
    missing = [k for k in ("DEEPGRAM_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")

    phone.dry_run = args.no_phone
    print("phone:", "dry-run" if args.no_phone else ("connected" if phone.check() else "NOT connected (adb devices is empty)"))

    from moopa.agent import Agent

    agent = Agent(use_mac_mic=(args.mic == "mac"))
    agent.navigator = phone.navigate
    server.actions["wake"] = agent.wake
    keys: dict = {}

    stop = threading.Event()
    threading.Thread(target=keyboard, args=(agent, keys, stop), daemon=True).start()
    print(f"Dashboard: http://127.0.0.1:{args.port}   |   SPACE = wake, q = quit")

    await asyncio.gather(agent.run(), server.serve(args.port))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
