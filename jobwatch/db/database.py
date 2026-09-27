import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Load configuration before any caller can construct the database engine. Keeping
# this here also covers manage.py and other entry points that import the DB layer.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required. Set it in .env to a PostgreSQL connection URL, "
        "for example postgresql+psycopg://user:password@localhost:5432/jobwatch."
    )

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


def sync_company_id_sequence(db) -> None:
    """Align PostgreSQL's company ID sequence after explicit-ID inserts."""
    if db.bind.dialect.name == "postgresql":
        db.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('company', 'id'), "
                "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM company"
            )
        )
