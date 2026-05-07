import logging
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging():
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        log = structlog.get_logger()
        log.info("request.start", request_id=rid, method=request.method, path=request.url.path)
        response = await call_next(request)
        log.info("request.end", request_id=rid, status=response.status_code)
        response.headers["x-request-id"] = rid
        return response
