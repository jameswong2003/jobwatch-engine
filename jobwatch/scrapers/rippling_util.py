from datetime import date
from typing import Dict

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json


def get_jobs(api_url: str) -> Dict:
    return request_json("GET", api_url, timeout=10)


def extract_jobs(json_data: Dict, company_id: int) -> list[JobCandidate]:
    jobs: list[JobCandidate] = []
    for job in json_data.get("items", []):
        job_url = job.get("url")
        job_id = str(job.get("id") or "")
        if not job_url:
            continue
        locations = job.get("locations")
        first_location = locations[0] if isinstance(locations, list) and locations else None
        location = first_location.get("country", "") if isinstance(first_location, dict) else ""
        jobs.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=job_id, job_date=date.today(),
            job_title=job.get("name") or "", active=True, location=location, date_added=date.today(),
        ))
    return jobs


def get_rippling_jobs(api_url: str, company_id: int, company_name: str = "") -> list[JobCandidate]:
    return extract_jobs(get_jobs(api_url), company_id)
