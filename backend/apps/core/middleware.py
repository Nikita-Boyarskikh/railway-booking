"""Custom middleware for the railway-booking project."""

import contextvars
import logging
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("apps.request")

X_REQUEST_ID_HEADER = "X-Request-ID"

# Thread-safe storage for request ID (used by the logging filter)
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDMiddleware:
    """Attach a unique request ID to every request/response cycle.

    If the client sends ``X-Request-ID``, it is reused; otherwise a new
    UUID4 is generated.  The ID is stored on ``request.request_id`` and
    returned in the ``X-Request-ID`` response header so callers can
    correlate logs with their requests.

    A logging filter (:class:`RequestIDFilter`) injects the ID into every
    log record emitted while the request is being processed.
    """

    get_response: Callable[[HttpRequest], HttpResponse]

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(X_REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]

        # Store on the thread-local so the logging filter can read it.
        _request_id_var.set(request_id)

        response = self.get_response(request)
        response[X_REQUEST_ID_HEADER] = request_id
        return response


class RequestLoggingMiddleware:
    """Log every request with method, path, status, and duration."""

    get_response: Callable[[HttpRequest], HttpResponse]

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "%s %s %s (%.0fms)",
            request.method,
            request.get_full_path(),
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.get_full_path(),
                "status": response.status_code,
                "duration_ms": round(duration_ms),
                "request_id": getattr(request, "request_id", "-"),
            },
        )
        return response


class RequestIDFilter(logging.Filter):
    """Inject ``request_id`` into every log record.

    Add ``%(request_id)s`` to any formatter to include the current
    request's correlation ID.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get("-")
        return True
