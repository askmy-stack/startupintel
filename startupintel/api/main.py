"""FastAPI application for StartupIntel."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from startupintel.api.routes import health, startup, investor, accelerator, termsheet, bot


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="StartupIntel API",
        version="0.2.0",
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

    # Include routers
    app.include_router(health.router)
    app.include_router(startup.router)
    app.include_router(investor.router)
    app.include_router(accelerator.router)
    app.include_router(termsheet.router)
    app.include_router(bot.router)

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

