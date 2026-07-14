from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Ensure model tables are registered on SQLModel.metadata
from app import models as _models  # noqa: F401


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


_ensure_parent(settings.db_path)
engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


def _migrate_sqlite() -> None:
    """Lightweight additive migrations for existing local SQLite files."""
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(attempt)").fetchall()
        cols = {row[1] for row in rows} if rows else set()
        if rows and "plan_item_id" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE attempt ADD COLUMN plan_item_id INTEGER"
            )
            conn.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
