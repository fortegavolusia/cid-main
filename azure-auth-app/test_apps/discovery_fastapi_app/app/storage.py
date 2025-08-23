import json
import os
from datetime import datetime, timezone
from typing import Tuple
from .models import Metadata, AppMeta, Endpoint


def ensure_dirs(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_metadata() -> Metadata:
    app_id = os.getenv("DISCOVERY_APP_ID", "")
    app_name = os.getenv("DISCOVERY_APP_NAME", "Discovery Test App")
    app_desc = os.getenv(
        "DISCOVERY_APP_DESCRIPTION",
        "Test app for generating CID-discoverable endpoints and fields",
    )
    return Metadata(
        app=AppMeta(
            app_id=app_id,
            app_name=app_name,
            app_description=app_desc,
            last_updated=now_iso(),
            endpoints=[],
        )
    )


def get_data_file() -> str:
    return os.getenv("DISCOVERY_DATA_FILE", os.path.join(os.path.dirname(__file__), "..", "data", "metadata.json"))


def load_metadata() -> Metadata:
    path = get_data_file()
    if not os.path.exists(path):
        ensure_dirs(path)
        md = default_metadata()
        save_metadata(md)
        return md
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Metadata.model_validate(data)


def save_metadata(metadata: Metadata) -> None:
    metadata.app.last_updated = now_iso()
    path = get_data_file()
    ensure_dirs(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, indent=2)


def add_endpoint(ep: Endpoint) -> Tuple[Metadata, int]:
    md = load_metadata()
    # de-dup by method+path
    existing = [(i, e) for i, e in enumerate(md.app.endpoints) if e.method == ep.method and e.path == ep.path]
    if existing:
        idx, _ = existing[0]
        md.app.endpoints[idx] = ep
        status = 200
    else:
        md.app.endpoints.append(ep)
        status = 201
    save_metadata(md)
    return md, status


def delete_endpoint(method: str, path: str) -> bool:
    md = load_metadata()
    before = len(md.app.endpoints)
    md.app.endpoints = [e for e in md.app.endpoints if not (e.method == method and e.path == path)]
    changed = len(md.app.endpoints) != before
    if changed:
        save_metadata(md)
    return changed

