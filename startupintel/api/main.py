"""FastAPI application for StartupIntel."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from startupintel.api.routes import health, startup, investor, accelerator, termsheet, bot, chat


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="StartupIntel API",
        version="0.3.0",
        description="Startup intelligence API powered by 8 specialized ML bots.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc) if app.debug else "An unexpected error occurred",
            },
        )

    return app


app = create_app()

