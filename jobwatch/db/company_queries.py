from jobwatch.db.init_db import SessionLocal
from jobwatch.models.Company import Company, JobBoardType
from jobwatch.models.Job import Job
from jobwatch.models.ErrorLog import ErrorLog
from typing import Optional

def get_all_companies() -> list[Company]:
    """Fetch all companies from the database using ORM."""
    db = SessionLocal()
    try:
        return db.query(Company).all()
    finally:
        db.close()

def get_company_by_name(name: str) -> Company:
    """Fetch a company by name using ORM."""
    db = SessionLocal()
    try:
        return db.query(Company).filter_by(company_name=name).first()
    finally:
        db.close()

def get_company_by_id(company_id: int) -> Optional[Company]:
    """Fetch a company by its database ID using ORM."""
    db = SessionLocal()
    try:
        return db.query(Company).filter_by(id=company_id).first()
    finally:
        db.close()

def insert_company(
    company_name: str,
    company_job_url: str,
    job_board_type: JobBoardType,
    has_api: bool = False,
    api_url: Optional[str] = None,
) -> int:
    """Insert a new company into the database using ORM."""
    db = SessionLocal()
    try:
        company = Company(
            company_name=company_name,
            company_job_url=company_job_url,
            job_board_type=job_board_type,
            has_api=has_api,
            api_url=api_url,
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company.id
    finally:
        db.close()


def upsert_companies(companies: list[dict]) -> dict[str, int]:
    """Insert or update companies by their explicit primary key.

    This intentionally does not delete companies that are absent from ``companies``.
    The caller is expected to validate and normalize each record before passing it in.
    Returns counts for inserted, updated, and unchanged records.
    """
    db = SessionLocal()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    try:
        for company_data in companies:
            company = db.get(Company, company_data["id"])
            if company is None:
                db.add(Company(**company_data))
                counts["inserted"] += 1
                continue

            changed = False
            for field in ("company_name", "company_job_url", "job_board_type", "has_api", "api_url"):
                value = company_data[field]
                if getattr(company, field) != value:
                    setattr(company, field, value)
                    changed = True

            counts["updated" if changed else "unchanged"] += 1

        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def delete_company_by_name(name: str) -> Optional[dict]:
    """
    Delete a company and all its dependent Job/ErrorLog rows by company_name.
    Returns a dict with counts of deleted rows, or None if no company with that name exists.
    SQLite foreign keys aren't enforced in this project, so dependent rows must be
    deleted explicitly rather than relying on ondelete=CASCADE.
    """
    db = SessionLocal()
    try:
        company = db.query(Company).filter_by(company_name=name).first()
        if company is None:
            return None

        deleted_jobs = db.query(Job).filter_by(company_id=company.id).delete()
        deleted_errors = db.query(ErrorLog).filter_by(company_id=company.id).delete()
        db.delete(company)
        db.commit()

        return {"jobs_deleted": deleted_jobs, "errors_deleted": deleted_errors}
    finally:
        db.close()

def update_company(
    name: str,
    new_name: Optional[str] = None,
    company_job_url: Optional[str] = None,
    job_board_type: Optional[JobBoardType] = None,
    has_api: Optional[bool] = None,
    api_url: Optional[str] = None,
) -> Optional[Company]:
    """
    Partially update a company by current name. Only non-None fields are changed.
    Returns the updated Company, or None if no company named `name` exists.
    """
    db = SessionLocal()
    try:
        company = db.query(Company).filter_by(company_name=name).first()
        if company is None:
            return None

        if new_name is not None:
            company.company_name = new_name
        if company_job_url is not None:
            company.company_job_url = company_job_url
        if job_board_type is not None:
            company.job_board_type = job_board_type
        if has_api is not None:
            company.has_api = has_api
        if api_url is not None:
            company.api_url = api_url

        db.commit()
        db.refresh(company)
        return company
    finally:
        db.close()
