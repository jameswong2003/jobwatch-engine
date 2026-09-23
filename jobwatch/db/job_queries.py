from jobwatch.db.init_db import SessionLocal
from jobwatch.models.Job import Job

from typing import Optional, List

def get_all_jobs():
    """Fetch all jobs from the database using ORM."""
    db = SessionLocal()
    try:
        return db.query(Job).all()
    finally:
        db.close()

def get_job_by_job_posting_url(job_posting_url: str) -> Optional[Job]:
    """Fetch a job by its job posting URL using ORM."""
    db = SessionLocal()
    try:
        return db.query(Job).filter_by(job_posting_url=job_posting_url).first()
    finally:
        db.close()

def get_existing_job_ids_for_company(company_id: int, job_ids: List[str]) -> set:
    """
    Given a company and a list of internal job IDs, return the subset already stored
    for that company. Used to dedupe a whole batch of scraped postings (e.g. Workday,
    which has no stable posting URL to key off of) in a single query.
    """
    if not job_ids:
        return set()

    db = SessionLocal()
    try:
        rows = (
            db.query(Job.job_id)
            .filter(Job.company_id == company_id, Job.job_id.in_(job_ids))
            .all()
        )
        return {row[0] for row in rows}
    finally:
        db.close()

def get_existing_job_posting_urls(job_posting_urls: List[str]) -> set:
    """
    Given a list of job posting URLs, return the subset that already exist in the database.
    Used to dedupe a whole batch of scraped postings in a single query instead of one
    query per posting.
    """
    if not job_posting_urls:
        return set()

    db = SessionLocal()
    try:
        rows = (
            db.query(Job.job_posting_url)
            .filter(Job.job_posting_url.in_(job_posting_urls))
            .all()
        )
        return {row[0] for row in rows}
    finally:
        db.close()

def insert_job_list(jobs: list[Job]) -> None:
    """
    Insert a list of jobs into the database using ORM.
    Each job in the list should be an instance of Job.
    """
    db = SessionLocal()
    try:
        db.add_all(jobs)
        db.commit()
        for job in jobs:
            _ = job.company  # eager-load before the session closes, so callers can
                              # still read job.company after insert_job_list returns
    finally:
        db.close()
