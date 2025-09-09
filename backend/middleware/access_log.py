"""FastAPI middleware that logs structured access logs for each request/response."""
from __future__ import annotations

import time
from typing import Callable
from fastapi import Request
import logging

from libs.logging_config import get_logging_config

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
            # Extract user/email if set by auth; fallback None
            user_email = None
            try:
                user_email = getattr(request.state, "user_email", None)
            except Exception:
                pass
            user_agent = request.headers.get("user-agent")
            client_ip = request.client.host if request.client else None

            # Emit structured fields via `extra` so JSON formatter includes them
            logger.info(
                "request",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "user_email": user_email,
                    "http_request_method": request.method,
                    "http_response_status_code": getattr(response, "status_code", None),
                    "url_path": request.url.path,
                    "duration_ms": duration_ms,
                    "source_ip": client_ip,
                    "user_agent_original": user_agent,
                },
            )
        except Exception:
            # Avoid breaking request on logging failure
            pass

