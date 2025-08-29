"""FastAPI middleware that logs structured access logs for each request/response."""
from __future__ import annotations

import time
from typing import Callable
from fastapi import Request
import logging

from backend.libs.logging_config import get_logging_config

logger = logging.getLogger("access")


async def access_log_middleware(request: Request, call_next: Callable):
    cfg = get_logging_config()
    if not cfg.get("access", {}).get("enabled", True):
        return await call_next(request)

    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        try:
            duration_ms = int((time.perf_counter() - start) * 1000)
            # Extract minimal user/email info from Authorization if our auth middleware sets it; fallback None
            user_email = None
            try:
                # If downstream set on request.state
                user_email = getattr(request.state, "user_email", None)
            except Exception:
                pass
            # Redact Authorization header
            user_agent = request.headers.get("user-agent")
            client_ip = request.client.host if request.client else None
            record = {
                "timestamp": None,  # logger formatter will add
                "event.category": "access",
                "service.name": "cids-backend",
                "http.request.method": request.method,
                "http.response.status_code": getattr(response, "status_code", None),
                "url.path": request.url.path,
                "duration.ms": duration_ms,
                "user.email": user_email,
                "source.ip": client_ip,
                "user_agent.original": user_agent,
            }
            logger.info("request", extra={
                "user_email": user_email,
                "request_id": getattr(request.state, "request_id", None),
            })
        except Exception:
            # Avoid breaking request on logging failure
            pass

