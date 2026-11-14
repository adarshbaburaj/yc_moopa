"""FastAPI: /state (JSON), /events (SSE), / (caregiver dashboard)."""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from moopa import state

DASH = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
app = FastAPI()
actions = {}  # name -> callable, set by run.py (e.g. "simulate_fall", "cancel_alert")


@app.get("/")
def index():
    return FileResponse(DASH)


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
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    snap = state.snapshot()["state"]
                    yield f"data: {json.dumps({'event': ev, 'state': snap})}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            state.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


async def serve(port: int = 8765):
    import uvicorn

    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    await uvicorn.Server(cfg).serve()
