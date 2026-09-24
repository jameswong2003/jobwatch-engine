from datetime import date, datetime

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json


def get_jobs(api_url: str) -> dict:
    return request_json("GET", api_url, timeout=10)


def extract_jobs(json_data: dict, company_id: int, company_name: str) -> list[JobCandidate]:
    jobs: list[JobCandidate] = []
    for job in json_data.get("content", []):
        job_id = job.get("uuid")
        if not job_id:
            continue
        try:
            released_date = job.get("releasedDate")
            job_date = datetime.fromisoformat(released_date.replace("Z", "+00:00")).date()
        except (AttributeError, TypeError, ValueError):
            job_date = date.today()
        location = job.get("location")
        if not isinstance(location, dict):
            location = {}
        jobs.append(JobCandidate(
            company_id=company_id,
            job_posting_url=f"https://jobs.smartrecruiters.com/oneclick-ui/company/{company_name}/publication/{job_id}",
            job_id=str(job_id), job_date=job_date, job_title=job.get("name") or "", active=True,
            location=location.get("fullLocation"), date_added=date.today(),
        ))
    return jobs


def get_smartrecruiters_jobs(api_url: str, company_id: int, company_name: str) -> list[JobCandidate]:
    return extract_jobs(get_jobs(api_url), company_id, company_name)
