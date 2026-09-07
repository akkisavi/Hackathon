"""SQLAlchemy engine/session setup.

`init_db()` enables the PostGIS extension and creates every table. We use
it instead of Alembic migrations for now — the schema is still moving fast
and `thermal_source` is rebuilt each run anyway. Run it once against a
fresh database:  python -m app.core.db
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Enable PostGIS and create all tables. Idempotent."""
    import app.models  # noqa: F401  -- register models on Base.metadata

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
    print(f"Schema ready on {engine.url.render_as_string(hide_password=True)}")
