from datetime import date

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json


def get_jobs(url: str, limit: int = 20, offset: int = 0, searchText: str = "") -> dict:
    json_body = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": searchText}
    return request_json("POST", url, json=json_body, timeout=10)


def extract_jobs(json_data: dict, company_id: int, company_job_url: str) -> list[JobCandidate]:
    jobs: list[JobCandidate] = []
    for posting in json_data.get("jobPostings", []):
        internal_job_id = str(posting.get("externalPath") or "")
        if not internal_job_id:
            continue
        jobs.append(JobCandidate(
            company_id=company_id, job_posting_url=f"{company_job_url}{internal_job_id}",
            job_id=internal_job_id, job_date=date.today(), job_title=posting.get("title", ""),
            active=True, location=posting.get("locationsText"), date_added=date.today(),
        ))
    return jobs


def get_workday_jobs(api_url: str, company_id: int, company_name: str, company_job_url: str) -> list[JobCandidate]:
    return extract_jobs(get_jobs(api_url), company_id, company_job_url)
