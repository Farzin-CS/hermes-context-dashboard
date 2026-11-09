"""Context Lens — dashboard backend.

Mounted at /api/plugins/context-lens/ by the Hermes web dashboard.
Reads the active profile's state.db read-only, off the event loop.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

import lens_core  # noqa: E402

router = APIRouter()

_CACHE: dict[tuple, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 8.0


def _overview_sync(days: int, source: str | None, archived: bool) -> dict[str, Any]:
    key = (days, source or "", archived)
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    with lens_core.Analyzer() as analyzer:
        payload = analyzer.overview(days=days, source=source, include_archived=archived)
    _CACHE[key] = (now, payload)
    return payload


@router.get("/health")
async def health() -> dict[str, Any]:
    try:
        path = lens_core.default_db_path()
        return {"ok": path.exists(), "db": str(path), "version": "0.1.0"}
    except Exception as exc:  # plugin contract: never raise out
        return {"ok": False, "error": type(exc).__name__}


@router.get("/overview")
async def overview(days: int = 30, source: str | None = None, archived: bool = False) -> dict[str, Any]:
    days = max(0, min(int(days), 3650))
    try:
        return await asyncio.to_thread(_overview_sync, days, source, archived)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


@router.get("/session/{session_id}")
async def session(session_id: str) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(_session_sync, session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown session") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


def _session_sync(session_id: str) -> dict[str, Any]:
    with lens_core.Analyzer() as analyzer:
        return analyzer.session(session_id)
