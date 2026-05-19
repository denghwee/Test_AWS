from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
try:
    from .config import settings
except ImportError:
    from config import settings  # type: ignore[no-redef]

# ── Engine ────────────────────────────────────────────────────────────────────

database_url = settings.database_url

# SQLite-specific: enable foreign key enforcement
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif database_url.startswith("postgresql"):
    if settings.DATABASE_SSLMODE:
        connect_args["sslmode"] = settings.DATABASE_SSLMODE
    if settings.database_sslrootcert_path:
        connect_args["sslrootcert"] = settings.database_sslrootcert_path

engine = create_engine(
    database_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

# Enable FK constraints for SQLite at connection level
if database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ── Session Factory ───────────────────────────────────────────────────────────

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base ──────────────────────────────────────────────────────────────────────

Base = declarative_base()

# ── Dependency Injection ──────────────────────────────────────────────────────

def get_db() -> Session:
    """
    FastAPI dependency that provides a database session per request.
    Automatically closes the session after the request completes.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
