"""Optional TurboQuant helper action.

This action is intentionally lightweight: it only reports support, prepares
cache directories, and returns future-loader environment hints.
"""

from __future__ import annotations

import json
from typing import Any


def turboquant_helper(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    from kree.core.turboquant_helper import (  # type: ignore[import]
        build_environment,
        detect_support,
        export_state,
        prepare_cache,
    )

    params: dict[str, Any] = parameters or {}
    action = str(params.get("action", "status") or "status").strip().lower()
    model_id = str(params.get("model_id", "") or "").strip()
    cache_root = str(params.get("cache_root", "") or "").strip() or None

    if player:
        player.write_log(f"[TurboQuant] {action} {model_id or ''}".strip())

    if action == "prepare_cache":
        result = prepare_cache(model_id=model_id, cache_root=cache_root)
    elif action == "environment":
        result = build_environment(model_id=model_id, cache_root=cache_root)
    elif action == "export":
        result = export_state(model_id=model_id, cache_root=cache_root)
    else:
        result = detect_support(model_id=model_id, cache_root=cache_root)

    pretty = json.dumps(result, indent=2, ensure_ascii=False)
    if player:
        player.write_log(f"[TurboQuant] Ready: {result.get('model_id') or 'no model'}")
    return pretty
