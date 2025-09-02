"""Disk persistence for token activity logs as JSONL to align with universal format."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from backend.libs.logging_config import get_logging_config
from backend.utils.paths import logs_path


def _current_file() -> Path:
    cfg = get_logging_config()
    dir_path = Path(cfg.get("token_activity", {}).get("path", str(logs_path("token_activity"))))
    dir_path.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().date().isoformat()
    return dir_path / f"token_activity_{today}.jsonl"


def append_token_activity(event: Dict[str, Any]) -> None:
    cfg = get_logging_config()
    if not cfg.get("token_activity", {}).get("persist_to_disk", True):
        return
    try:
        f = _current_file()
        with f.open("a") as fh:
            fh.write(json.dumps(event) + "\n")
    except Exception:
        # swallow errors to avoid impacting request path
        pass

