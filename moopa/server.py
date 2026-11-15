"""FastAPI: /state (JSON), /events (SSE), / (caregiver dashboard)."""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from moopa import console  # noqa: E402
from moopa import state

DASH = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
app = FastAPI()
actions = {}  # name -> callable, set by run.py (e.g. "simulate_fall", "cancel_alert")


@app.get("/")
def index():
    return FileResponse(DASH)


@app.get("/stop")
def stop_page():
    return FileResponse(DASH.parent / "stop.html")


@app.get("/signups")
def signups_page():
    return FileResponse(DASH.parent / "signups.html")


@app.get("/signups.json")
def signups_data():
    return FileResponse(DASH.parent / "signups.json")


@app.get("/state")
def get_state():
    return JSONResponse(state.snapshot())


@app.post("/action/{name}")
def do_action(name: str):
    fn = actions.get(name)
    if not fn:
        return JSONResponse({"ok": False, "error": "unknown action"}, status_code=404)
    fn()
    return {"ok": True}


@app.get("/events")
async def events():
    q = state.subscribe()

    async def gen():
        try:
            yield f"data: {json.dumps({'kind': 'hello'})}\n\n"
            sent, quiet = -1, 0.0
            while True:
                try:  # events go out at once; state changes with no event (vitals, steps, awake) within 0.25 s
                    ev = await asyncio.wait_for(q.get(), timeout=0.25)
                    sent, quiet = state.version, 0.0
                    yield f"data: {json.dumps({'event': ev, 'state': state.snapshot()['state']})}\n\n"
                except asyncio.TimeoutError:
                    if state.version != sent:
                        sent, quiet = state.version, 0.0
                        yield f"data: {json.dumps({'state': state.snapshot()['state']})}\n\n"
                    else:
                        quiet += 0.25
                        if quiet >= 15:
                            quiet = 0.0
                            yield ": ping\n\n"
        finally:
            state.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


def free_port(start: int = 8765) -> int:
    import socket

    for port in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


async def serve(port: int = 8765):
    """Never takes the agent down: a server problem is printed, not raised."""
    import uvicorn

    try:
        cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        await uvicorn.Server(cfg).serve()
    except (SystemExit, Exception) as e:
        console.log(f"[server] dashboard stopped: {e!r} (agent keeps running)")
