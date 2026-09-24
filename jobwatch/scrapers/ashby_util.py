from datetime import date, datetime

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json


def get_jobs(api_url: str) -> dict:
    return request_json("GET", api_url, timeout=10)


def extract_jobs(json_data: dict, company_id: int) -> list[JobCandidate]:
    jobs_data = json_data.get("jobs", [])
    jobs: list[JobCandidate] = []
    for job in jobs_data:
        job_url = job.get("jobUrl")
        if not job_url:
            continue
        published_date = job.get("publishedAt")
        try:
            job_date = datetime.fromisoformat(published_date).date() if published_date else date.today()
        except (TypeError, ValueError):
            job_date = date.today()
        jobs.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=str(job.get("id") or ""),
            job_date=job_date, job_title=job.get("title") or "",
            active=True, location=job.get("location"), date_added=date.today(),
        ))
    return jobs


def get_ashby_jobs(api_url: str, company_id: int, company_name: str = "") -> list[JobCandidate]:
    return extract_jobs(get_jobs(api_url), company_id)
