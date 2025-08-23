import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict
from .models import Metadata, Endpoint, FieldMeta
from .storage import load_metadata, save_metadata, add_endpoint, delete_endpoint

app = FastAPI(title="CID Discovery Test App", version="1.0.0")

# Mount static UI
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def ui_index():
    # very simple static page served
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# Discovery endpoint (no auth)
@app.get("/discovery/endpoints")
def discovery(version: str = "2.0"):
    md = load_metadata()
    if version != "2.0":
        # Backwards compatibility minimal v1
        return {
            "version": "1.0",
            "app_name": md.app.app_name,
            "endpoints": [
                {"method": e.method, "path": e.path, "description": e.description or ""}
                for e in md.app.endpoints
            ],
        }

    # v2 format
    return {
        "version": "2.0",
        "app_id": md.app.app_id,
        "app_name": md.app.app_name,
        "app_description": md.app.app_description,
        "last_updated": md.app.last_updated,
        "endpoints": [e.model_dump(exclude_none=True) for e in md.app.endpoints],
    }


# API to manage metadata (no auth, local tool)
class UpsertEndpointReq(BaseModel):
    method: str
    path: str
    operation_id: Optional[str] = None
    description: Optional[str] = None
    request_fields: Optional[Dict[str, FieldMeta]] = None
    response_fields: Optional[Dict[str, FieldMeta]] = None


@app.post("/admin/endpoints")
def upsert_endpoint(body: UpsertEndpointReq):
    try:
        ep = Endpoint(**body.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    md, status = add_endpoint(ep)
    return {"status": status, "endpoint": ep.model_dump(exclude_none=True)}


@app.delete("/admin/endpoints")
def remove_endpoint(method: str, path: str):
    ok = delete_endpoint(method, path)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": 200}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DISCOVERY_PORT", "5002"))
    uvicorn.run(app, host="0.0.0.0", port=port)

