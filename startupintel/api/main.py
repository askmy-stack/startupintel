"""FastAPI application for StartupIntel."""

import logging
import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from startupintel.api.routes import health, startup, investor, accelerator, termsheet, bot, chat
from startupintel.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="StartupIntel API",
        version="0.3.0",
        description="Startup intelligence API powered by 8 specialized ML bots.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware - configured via environment for production safety
    settings = get_settings()
    allow_origins = settings.cors_allowed_origins.split(",") if settings.cors_allowed_origins else ["http://localhost:3000", "http://localhost:8080"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=600,
    )

    # Gzip compression for responses > 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request ID middleware for tracing
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        
        # Add request ID and timing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str(round((time.time() - start_time) * 1000, 2))
        
        # Log request details
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {request_id}"
        )
        
        return response

    # Get the base directory for static files
    base_dir = Path(__file__).parent.parent
    static_dir = base_dir / "static"
    
    # Mount static files if directory exists
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    app.include_router(health.router, prefix="/api")
    app.include_router(startup.router, prefix="/api")
    app.include_router(investor.router, prefix="/api")
    app.include_router(accelerator.router, prefix="/api")
    app.include_router(termsheet.router, prefix="/api")
    app.include_router(bot.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")

    # Serve UI at root
    @app.get("/")
    async def serve_ui():
        """Serve the main UI."""
        ui_file = static_dir / "index.html"
        if ui_file.exists():
            return FileResponse(str(ui_file))
        return {"message": "StartupIntel API", "docs": "/docs", "ui": "/static/index.html"}

    # Global exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc) if app.debug else "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    return app


app = create_app()

