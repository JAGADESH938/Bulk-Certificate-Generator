import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.certificates import router as certificates_router
from app.api.routes.jobs import router as jobs_router
from app.core.config import settings
from app.core.database import Base, engine
from app.services.storage_service import storage_service

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bulk_certificate_app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    logger.info("Initializing Bulk Certificate Generator application...")
    # Ensure storage directories exist
    storage_service.base_dir.mkdir(parents=True, exist_ok=True)
    
    # In development / sqlite mode, ensure tables exist if not running alembic
    

    logger.info("Application startup completed successfully.")
    yield
    logger.info("Shutting down Bulk Certificate Generator application.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "Production-grade asynchronous bulk certificate generation engine. "
        "Accepts bulk recipient payloads, processes certificates concurrently with "
        "independent transaction boundaries, tracks progress, and serves downloadable PDFs."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format Pydantic / FastAPI validation errors into clean, consistent client responses."""
    error_messages = []
    for err in exc.errors():
        location = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_messages.append(f"{location}: {msg}")

    detail_str = "; ".join(error_messages) if error_messages else "Invalid request payload"
    logger.warning("Validation failed for %s %s: %s", request.method, request.url.path, detail_str)

    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail_str},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Ensure all HTTP exceptions return uniform JSON error structures."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled runtime errors, log full trace internally, and hide secrets from client."""
    logger.exception("Unhandled internal exception during request to %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system support."},
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Application health check",
    description="Check liveness and operational readiness of the API.",
)
def health_check() -> dict[str, str]:
    return {"status": "healthy", "project": settings.PROJECT_NAME}


# Include versioned API routers
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(certificates_router, prefix=settings.API_V1_PREFIX)
