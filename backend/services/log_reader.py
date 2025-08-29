"""Helpers to read structured JSON logs from files with simple filtering and paging."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from datetime import datetime

from backend.libs.logging_config import get_logging_config


ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        # Support subsecond and whole second
        if value.endswith("Z") and "." not in value:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return datetime.strptime(value, ISO)
    except Exception:
        return None


def _iter_lines(paths: List[Path]) -> Iterable[str]:
    for p in paths:
        if p.exists() and p.is_file():
            try:
                with p.open("r") as f:
                    for line in f:
                        if line.strip():
                            yield line
            except Exception:
                continue


def read_app_logs(
    start: Optional[str] = None,
    end: Optional[str] = None,
    level: Optional[List[str]] = None,
    logger_prefix: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Read structured app logs (JSON) from current log file and recent backups.
    Returns newest first up to `limit` items matching filters.
    """
    cfg = get_logging_config()
    file_cfg = cfg.get("app", {}).get("file", {})
    path = Path(file_cfg.get("path", ""))
    backups = int(file_cfg.get("rotation", {}).get("backup_count", 3))

    files: List[Path] = [path]
    # RotatingFileHandler names backups like app.log.1, .2 ...
    for i in range(1, backups + 1):
        files.append(path.with_name(f"{path.name}.{i}"))

    # We will collect and then sort by timestamp desc
    items: List[Dict[str, Any]] = []
    ts_start = _parse_ts(start) if start else None
    ts_end = _parse_ts(end) if end else None
    level_set = set(l.upper() for l in (level or []))
    q_lower = (q or "").lower()

    for line in _iter_lines(files):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        ts = _parse_ts(obj.get("timestamp", ""))
        if ts_start and (not ts or ts < ts_start):
            continue
        if ts_end and (not ts or ts > ts_end):
            continue
        if level_set and str(obj.get("level", "")).upper() not in level_set:
            continue
        if logger_prefix and not str(obj.get("logger", "")).startswith(logger_prefix):
            continue
        if q_lower:
            # naive contains over message and details
            msg = str(obj.get("message", ""))
            if q_lower not in msg.lower() and q_lower not in json.dumps(obj).lower():
                continue
        items.append(obj)

    # Newest first by timestamp
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return items[: max(1, min(limit, 1000))]

