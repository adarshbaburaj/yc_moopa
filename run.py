"""Start Moopa. Every part can run without the others.

  python run.py                        sim band, Mac mic, sim ring, camera on, real phone
  python run.py --no-phone --no-camera print phone actions instead of doing them
  python run.py --band real --mic band real band (number from BAND_NUMBER in .env)

Keys in the terminal: SPACE = start/stop listening (like a band double-tap),
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
    ap.add_argument("--voice", choices=["phone", "mac"], default="phone",
                    help="where the agent speaks: the phone's speaker (halo-app) or the Mac")
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
                state.emit("system", "Space bar")
                agent.toggle()
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
    need = ["DEEPGRAM_API_KEY"] + (["GOOGLE_CLOUD_PROJECT"] if os.getenv("LLM_PROVIDER", "openai") == "gemini"
                                   else ["OPENAI_API_KEY"])
    missing = [k for k in need if not os.getenv(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")

    phone.dry_run = args.no_phone
    print("phone:", "dry-run" if args.no_phone else ("connected" if phone.check() else "NOT connected (adb devices is empty)"))

    from moopa.agent import Agent, llm_provider
    from moopa.fall import FallResponder

    if args.mic == "band" and args.band == "off":
        sys.exit("--mic band needs a band: use --band real or --band sim")
    voice_phone = args.voice == "phone" and not args.no_phone and phone.check() and phone.start_phone_voice()
    agent = Agent(use_mac_mic=(args.mic == "mac"), voice_on_phone=bool(voice_phone))
    agent.navigator = phone.navigate
    falls = FallResponder(agent)
    agent.on_alert = falls.alert
    agent.transcript_hooks.append(falls.on_transcript)

    band = None
    if args.band != "off":
        from moopa.band import BandLink

        band = BandLink(agent, sim=(args.band == "sim"), use_band_mic=(args.mic == "band"))
        band.double_tap_hooks.append(falls.on_double_tap)
        band.fall_hooks.append(falls.trigger)
        band.start()

    def pretend_fall():
        if band and band.band and band.sim:
            band.sim_fall()  # goes through the band's real free-fall + stillness logic
        else:
            falls.trigger("band")

    def double_tap():
        if band and band.band and band.sim:
            band.sim_double_tap()
        elif not falls.on_double_tap():
            agent.toggle()

    server.actions.update({"wake": lambda: agent.wake(hold=True), "stop": agent.stop_listening, "fall": pretend_fall, "cancel": falls.reset,
                           "double_tap": double_tap})
    keys = {"d": double_tap, "f": pretend_fall, "c": falls.reset}

    stop = threading.Event()
    threading.Thread(target=keyboard, args=(agent, keys, stop), daemon=True).start()
    port = server.free_port(args.port)
    if port != args.port:
        print(f"[server] port {args.port} is busy (an old run.py still open?) -> using {port}")
    print(f"brain: {llm_provider()} | band: {args.band} | mic: {args.mic} | "
          f"voice: {'phone speaker' if voice_phone else 'Mac'}")
    print(f"Dashboard: http://127.0.0.1:{port}   |   SPACE = start/stop listening, d = double-tap, f = pretend fall, "
          f"c = cancel alert, q = quit")

    await asyncio.gather(agent.run(), server.serve(port))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
