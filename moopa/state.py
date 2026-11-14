"""Shared state + event bus.

Everything (band thread, ring thread, camera subprocess reader, agent, server) writes
here. Thread-safe. The server streams `events` over SSE; `/state` returns `snapshot()`.
"""

import asyncio
import threading
import time
from collections import deque

_lock = threading.RLock()
_subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
_listeners: list = []  # plain callables(event) run in the emitter's thread: keep them tiny

state = {
    "status": "OK",  # OK | CHECKING | ALERT
    "alert": None,  # {"reason", "confirmed", "description", "ts"}
    "awake": False,
    "vitals": {"heart_rate": None, "spo2": None, "source": None, "ts": None},
    "activity": {"steps": 0, "active_s": 0.0, "still_s": 0.0, "current": None, "falls": 0},
    "devices": {"band": "off", "ring": "off", "camera": "off", "phone": "off", "mic": "mac"},
    "pending_confirmation": None,
    "working": None,  # what the agent is doing on the phone right now, for the mascot
}
events: deque = deque(maxlen=300)


def emit(kind: str, text: str, **data) -> dict:
    """Record one event: kind is e.g. 'transcript', 'agent', 'action', 'fall', 'vitals', 'system'."""
    ev = {"ts": time.time(), "kind": kind, "text": text, **data}
    with _lock:
        events.append(ev)
        subs = list(_subscribers)
        listeners = list(_listeners)
    for loop, q in subs:
        try:
            loop.call_soon_threadsafe(q.put_nowait, ev)
        except RuntimeError:
            pass
    for fn in listeners:
        try:
            fn(ev)
        except Exception as e:  # a listener must never break the emitter
            print(f"[state] listener error: {e}")
    return ev


def update(path: str, value) -> None:
    """update('vitals.heart_rate', 72)"""
    with _lock:
        d = state
        *parents, last = path.split(".")
        for p in parents:
            d = d[p]
        d[last] = value


def merge(section: str, values: dict) -> None:
    with _lock:
        state[section].update(values)


def get(path: str):
    with _lock:
        d = state
        for p in path.split("."):
            d = d[p]
        return d


def snapshot() -> dict:
    import copy

    with _lock:
        return {"state": copy.deepcopy(state), "events": list(events)[-100:]}


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    with _lock:
        _subscribers.append((asyncio.get_running_loop(), q))
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    with _lock:
        _subscribers[:] = [(l, s) for l, s in _subscribers if s is not q]


def add_listener(fn) -> None:
    with _lock:
        _listeners.append(fn)
