from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import router
from app.lifecycle_api import router as lifecycle_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import DomainError, domain_error_handler

settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID", "X-Device-Label"],
)
app.add_exception_handler(DomainError, domain_error_handler)
app.include_router(router)
app.include_router(lifecycle_router)

@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/ready")
def ready() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except SQLAlchemyError:
        return JSONResponse({"status": "not_ready"}, status_code=503)
