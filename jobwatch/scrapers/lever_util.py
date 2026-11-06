import logging
from datetime import date, datetime, timezone
from typing import Dict, List
from urllib.parse import quote, urlsplit

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json

logger = logging.getLogger(__name__)


def get_jobs(api_url: str) -> List[Dict]:
    return request_json("GET", api_url, timeout=10)


def extract_jobs(json_data: List[Dict], company_id: int) -> list[JobCandidate]:
    jobs: list[JobCandidate] = []
    for job in json_data:
        job_url = job.get("hostedUrl")
        if not job_url:
            continue
        created_at = job.get("createdAt")
        try:
            job_date = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).date() if created_at else date.today()
        except (OverflowError, TypeError, ValueError):
            job_date = date.today()
        categories = job.get("categories")
        if not isinstance(categories, dict):
            categories = {}
        jobs.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=str(job.get("id") or ""),
            job_date=job_date, job_title=job.get("text") or "", active=True,
            location=categories.get("location"), date_added=date.today(),
        ))
    return jobs


def get_lever_jobs(api_url: str, company_id: int, company_name: str = "") -> list[JobCandidate]:
    return extract_jobs(get_jobs(api_url), company_id)


def is_lever_job_active(api_url: str | None, job_id: str | None) -> bool:
    """Return whether a Lever posting can be fetched; any check error is inactive."""
    try:
        if not isinstance(api_url, str) or not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("Lever API URL and job ID are required")
        parsed = urlsplit(api_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.path.rstrip("/").endswith("/postings"):
            raise ValueError("Invalid Lever API URL")
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}/{quote(job_id.strip(), safe='')}"
        response = request_json("GET", url, timeout=10)
        if not isinstance(response, dict):
            raise ValueError("Lever returned an invalid job response")
        return True
    except Exception as error:
        logger.warning("Lever job check failed api_url=%s job_id=%s error=%s", api_url, job_id, error)
        return False
