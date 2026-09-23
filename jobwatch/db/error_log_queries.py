from jobwatch.db.init_db import SessionLocal
from jobwatch.models.ErrorLog import ErrorLog


def insert_error_log_list(errors: list[ErrorLog]) -> None:
    """Insert a list of error log entries into the database using ORM."""
    if not errors:
        return

    db = SessionLocal()
    try:
        db.add_all(errors)
        db.commit()
    finally:
        db.close()
