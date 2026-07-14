import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """Bundled read-only resources (problems.json, static UI)."""
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Writable runtime data (SQLite)."""
    if _is_frozen() or os.environ.get("COACH_PORTABLE") == "1":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        path = base / "PeachAlgoCoach"
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(__file__).resolve().parent.parent / "data"


RESOURCE_DIR = resource_dir()
USER_DATA_DIR = user_data_dir()
DEFAULT_DB_PATH = USER_DATA_DIR / "coach.db"
DEFAULT_PROBLEMS_PATH = RESOURCE_DIR / "data" / "problems.json"
# Dev fallback: if backend/data/problems.json exists (non-frozen layout)
if not DEFAULT_PROBLEMS_PATH.exists():
    alt = Path(__file__).resolve().parent.parent / "data" / "problems.json"
    if alt.exists():
        DEFAULT_PROBLEMS_PATH = alt

DEFAULT_STATIC_DIR = RESOURCE_DIR / "static"
if not DEFAULT_STATIC_DIR.exists():
    # Allow serving a local frontend build without packaging
    alt_static = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if alt_static.exists():
        DEFAULT_STATIC_DIR = alt_static


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COACH_", extra="ignore")

    app_name: str = "PeachAlgo Coach"
    db_path: str = str(DEFAULT_DB_PATH)
    problems_path: str = str(DEFAULT_PROBLEMS_PATH)
    static_dir: str = str(DEFAULT_STATIC_DIR)
    host: str = "127.0.0.1"
    port: int = 8765
    open_browser: bool = True
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ]


settings = Settings()
