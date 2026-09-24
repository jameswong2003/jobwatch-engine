from datetime import date, datetime, timezone
from typing import Dict, List

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json


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
