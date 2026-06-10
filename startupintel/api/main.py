from fastapi import FastAPI

from startupintel.api.routes import accelerator, health, investor, startup, termsheet


def create_app() -> FastAPI:
    app = FastAPI(
        title="StartupIntel API",
        version="0.1.0",
        description="Startup intelligence API powered by specialized ML bots.",
    )
    app.include_router(health.router)
    app.include_router(startup.router)
    app.include_router(investor.router)
    app.include_router(accelerator.router)
    app.include_router(termsheet.router)
    return app


app = create_app()

