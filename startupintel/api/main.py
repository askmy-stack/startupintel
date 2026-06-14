from fastapi import FastAPI

from startupintel.api.routes import (
    accelerator,
    auth,
    bot,
    chat,
    export,
    feature_flags,
    health,
    investor,
    metrics,
    startup,
    termsheet,
    websocket,
)


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
    app.include_router(auth.router)
    app.include_router(websocket.router)
    app.include_router(export.router)
    app.include_router(metrics.router)
    app.include_router(feature_flags.router)
    app.include_router(chat.router)
    app.include_router(bot.router)
    return app


app = create_app()
