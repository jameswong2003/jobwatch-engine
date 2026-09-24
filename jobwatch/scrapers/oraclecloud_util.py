from datetime import date, datetime
from urllib.parse import urlparse

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json


def get_jobs(api_url: str) -> tuple[dict, str]:
    parsed = urlparse(api_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return request_json("GET", api_url, timeout=10), base_url


def extract_jobs(json_data: dict, company_id: int, base_url: str) -> list[JobCandidate]:
    jobs_data = json_data.get("items", [])[0].get("requisitionList", [])
    jobs: list[JobCandidate] = []
    for job in jobs_data:
        job_id = job.get("Id")
        if job_id is None:
            continue
        job_url = f"{base_url}/hcmUI/CandidateExperience/en/sites/CX_1001/job/{job_id}"
        try:
            job_date = datetime.strptime(job.get("PostedDate"), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            job_date = date.today()
        jobs.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=str(job_id),
            job_date=job_date,
            job_title=job.get("Title") or "", active=True, location=job.get("PrimaryLocation", ""),
            date_added=date.today(),
        ))
    return jobs


def get_oracle_cloud_jobs(api_url: str, company_id: int, company_name: str = "") -> list[JobCandidate]:
    json_data, base_url = get_jobs(api_url)
    return extract_jobs(json_data, company_id, base_url)
