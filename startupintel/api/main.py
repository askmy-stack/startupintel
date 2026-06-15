from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from startupintel.api.routes import (
    accelerator,
    auth,
    bot,
    chat,
    export,
    feature_flags,
    files,
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
    app.include_router(files.router)

    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui() -> object:
        """Serve the dashboard UI when present, else a small API pointer."""
        ui_file = static_dir / "index.html"
        if ui_file.exists():
            return FileResponse(str(ui_file))
        return {"message": "StartupIntel API", "docs": "/docs", "ui": "/static/index.html"}

    return app


app = create_app()
