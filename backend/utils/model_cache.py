"""Utility to fetch and cache LLM model lists from providers."""

from __future__ import annotations

import asyncio
import httpx
import time
from typing import Dict, List, Tuple

_CACHE: Dict[str, Tuple[float, List[str]]] = {}
_DEFAULT_TTL = 60 * 60  # 1 hour


async def get_models(provider: str, fetch_fn, ttl: int = _DEFAULT_TTL) -> List[str]:
    """Return cached models for provider or fetch using *fetch_fn*.

    fetch_fn must be an async callable returning List[str].
    """
    now = time.time()
    # Return cached if fresh
    if provider in _CACHE:
        ts, models = _CACHE[provider]
        if now - ts < ttl:
            return models

    # Fetch and cache
    models = await fetch_fn()
    _CACHE[provider] = (now, models)
    return models 