"""Quiet by default: internal chatter only with run.py --verbose. The ready line always shows."""

import sys

VERBOSE = False


def log(*args, **kwargs) -> None:
    if VERBOSE:
        print(*args, **kwargs, flush=True)


def show(*args, **kwargs) -> None:
    print(*args, **kwargs, flush=True)


def quiet_libraries() -> None:
    """Pipecat logs through loguru; Google libs warn. Keep only real errors unless --verbose."""
    import warnings

    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if VERBOSE else "ERROR",
               format="{time:HH:mm:ss} | {level} | {message}")
    if not VERBOSE:
        warnings.filterwarnings("ignore")
