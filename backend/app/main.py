from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # Heal roadmap items accidentally deferred by older withdraw logic.
    try:
        from sqlmodel import Session

        from app.db import engine
        from app.services.planner import repair_withdrawn_roadmap_items

        with Session(engine) as session:
            repair_withdrawn_roadmap_items(session)
    except Exception:
        pass
    yield


def _static_dir() -> Path | None:
    path = Path(settings.static_dir)
    if path.is_dir() and (path / "index.html").exists():
        return path
    return None


def create_app() -> FastAPI:
    # Eager init so TestClient and simple scripts work without lifespan context.
    init_db()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins + ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    static = _static_dir()
    if static is not None:
        assets = static / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/")
        def spa_root() -> FileResponse:
            return FileResponse(static / "index.html")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            # API routes are registered above; this only catches UI paths.
            if full_path.startswith("api/") or full_path in {"docs", "openapi.json", "redoc"}:
                raise HTTPException(status_code=404, detail="Not Found")
            candidate = static / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(static / "index.html")
    else:

        @app.get("/")
        def root() -> dict[str, str]:
            return {
                "name": settings.app_name,
                "docs": "/docs",
                "health": "/api/health",
            }

    return app


app = create_app()
