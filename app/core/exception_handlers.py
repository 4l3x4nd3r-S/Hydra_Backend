import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("hydra.core.errors")


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "http.400 path=%s detail=%r request_id=%s",
        request.url.path,
        str(exc),
        request_id,
    )
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "code": "BUSINESS_RULE_VIOLATION",
            "request_id": request_id,
        },
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "http.500 path=%s request_id=%s",
        request.url.path,
        request_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor.",
            "code": "INTERNAL_SERVER_ERROR",
            "request_id": request_id,
        },
    )
