from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass(slots=True)
class DomainError(Exception):
    code: str
    message: str
    status_code: int = 400


class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__("NOT_FOUND", message, 404)


class AuthorizationError(DomainError):
    def __init__(self, message: str = "Not authorized") -> None:
        super().__init__("FORBIDDEN", message, 403)


class ConflictError(DomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, 409)


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            },
        },
    )
