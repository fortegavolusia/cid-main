"""Centralized logging configuration for CIDS backend.
Sets up application logging (JSON + rotation) and exposes runtime-config APIs.
"""
from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from backend.utils.paths import logs_path, config_path


DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "level": os.getenv("LOG_LEVEL", "DEBUG" if os.getenv("DEV", "true").lower() == "true" else "INFO"),
        "json": True,
        "stdout": True,
        "file": {
            "enabled": True,
            "path": str(logs_path("app", "app.log")),
            "rotation": {"max_bytes": 20_000_000, "backup_count": 10},
        },
        "module_levels": {"httpx": "WARNING", "uvicorn": "WARNING"},
    },
    "audit": {
        "enabled": True,
        "path": str(logs_path("audit")),
        "retention_days": 90,
    },
    "token_activity": {
        "enabled": True,
        "persist_to_disk": True,
        "path": str(logs_path("token_activity")),
        "retention_days": 60,
    },
    "access": {
        "enabled": True,
        "path": str(logs_path("access")),
        "retention_days": 30,
    },
    "privacy": {
        "redact_auth_headers": True,
        "truncate_ids": True,
    },
}

_CONFIG_FILE = config_path("logging.json")
_CURRENT_CONFIG: Dict[str, Any] = {}


class JSONFormatter(logging.Formatter):
    def __init__(self, service_name: str = "cids-backend"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "service.name": self.service_name,
            "message": record.getMessage(),
        }
        # Attach extras if present
        for key in ("request_id", "trace_id", "span_id", "user_email"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key.replace("_", ".")] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _load_config_from_disk() -> Dict[str, Any]:
    try:
        if Path(_CONFIG_FILE).exists():
            with open(_CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data
    except Exception:
        # Fall back to defaults on any error
        pass
    return DEFAULT_CONFIG.copy()


def get_logging_config() -> Dict[str, Any]:
    # Return a copy to avoid external mutation
    return json.loads(json.dumps(_CURRENT_CONFIG))


def _ensure_dirs(cfg: Dict[str, Any]) -> None:
    # Ensure directories exist for configured paths
    try:
        app_file = cfg.get("app", {}).get("file", {}).get("path")
        if app_file:
            Path(app_file).parent.mkdir(parents=True, exist_ok=True)
        for key in ("audit", "token_activity", "access"):
            p = cfg.get(key, {}).get("path")
            if p:
                Path(p).mkdir(parents=True, exist_ok=True)
    except Exception:
        # Don't crash on startup for directory issues
        pass


def _apply_logging_config(cfg: Dict[str, Any]) -> None:
    _ensure_dirs(cfg)

    # Root logger
    root = logging.getLogger()
    # Remove existing non-uvicorn handlers to avoid dupes
    for h in list(root.handlers):
        root.removeHandler(h)

    level = getattr(logging, str(cfg["app"]["level"]).upper(), logging.INFO)
    root.setLevel(level)

    # JSON formatter
    if cfg["app"].get("json", True):
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File handler
    file_cfg = cfg["app"].get("file", {})
    if file_cfg.get("enabled", True) and file_cfg.get("path"):
        max_bytes = int(file_cfg.get("rotation", {}).get("max_bytes", 20_000_000))
        backups = int(file_cfg.get("rotation", {}).get("backup_count", 10))
        fh = RotatingFileHandler(file_cfg["path"], maxBytes=max_bytes, backupCount=backups)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    # Stdout handler
    if cfg["app"].get("stdout", True):
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # Module-specific levels
    for module_name, lvl in cfg["app"].get("module_levels", {}).items():
        logging.getLogger(module_name).setLevel(getattr(logging, lvl.upper(), logging.INFO))


def setup_logging(initial_config: Optional[Dict[str, Any]] = None) -> None:
    global _CURRENT_CONFIG
    cfg = initial_config or _load_config_from_disk()
    _CURRENT_CONFIG = cfg
    _apply_logging_config(cfg)


def update_logging_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow-merge update to logging config and apply at runtime."""
    global _CURRENT_CONFIG
    cfg = get_logging_config()
    # Shallow merge (nested dicts handled one level deep for our needs)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    _CURRENT_CONFIG = cfg
    # Persist to disk
    try:
        Path(_CONFIG_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(_CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass
    # Apply live
    _apply_logging_config(cfg)
    return get_logging_config()

