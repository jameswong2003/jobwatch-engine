from jobwatch.db.init_db import SessionLocal
from jobwatch.models.Job import Job
from jobwatch.scrapers.job_candidate import JobCandidate

from typing import Optional, List


_SQLITE_QUERY_BATCH_SIZE = 500


def _chunks(values: List[str], size: int = _SQLITE_QUERY_BATCH_SIZE):
    for start in range(0, len(values), size):
        yield values[start:start + size]

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
        existing_urls = set()
        for batch in _chunks(job_posting_urls):
            rows = (
                db.query(Job.job_posting_url)
                .filter(Job.job_posting_url.in_(batch))
                .all()
            )
            existing_urls.update(row[0] for row in rows)
        return existing_urls
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


def materialize_new_job_candidates(candidates: list[JobCandidate]) -> list[Job]:
    """Filter candidates against SQLite and convert only new rows to ORM jobs.

    Posting URL is the single identity key for every provider. Scrapers deliberately
    return candidates without querying SQLite; this standalone adapter filters them
    in a batched URL lookup before constructing ORM rows.
    """
    if not candidates:
        return []

    urls = list(dict.fromkeys(candidate.job_posting_url for candidate in candidates if candidate.job_posting_url))
    existing_urls = get_existing_job_posting_urls(urls)

    new_jobs: list[Job] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if not candidate.job_posting_url or candidate.job_posting_url in existing_urls or candidate.job_posting_url in seen_urls:
            continue
        seen_urls.add(candidate.job_posting_url)
        new_jobs.append(Job(
            company_id=candidate.company_id,
            job_posting_url=candidate.job_posting_url,
            job_id=candidate.job_id,
            job_date=candidate.job_date,
            job_title=candidate.job_title,
            active=candidate.active,
            location=candidate.location,
            date_added=candidate.date_added,
            category=candidate.category,
        ))
    return new_jobs
