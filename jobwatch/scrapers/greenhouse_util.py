from datetime import date, datetime
from typing import Any
from urllib.parse import quote, urlsplit

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import HTTPResponseError, request_json


def get_jobs(api_url: str) -> dict:
    return request_json("GET", api_url, timeout=10)


def extract_jobs(json_data: dict, company_id: int) -> list[JobCandidate]:
    jobs: list[JobCandidate] = []
    for job in json_data.get("jobs", []):
        job_url = job.get("absolute_url")
        if not job_url:
            continue
        updated_at = job.get("updated_at")
        try:
            job_date = datetime.fromisoformat(updated_at).date() if updated_at else date.today()
        except (TypeError, ValueError):
            job_date = date.today()
        location = job.get("location")
        if not isinstance(location, dict):
            location = {}
        jobs.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=str(job.get("id") or ""),
            job_date=job_date, job_title=job.get("title") or "", active=True,
            location=location.get("name", "Unknown Location"), date_added=date.today(),
        ))
    return jobs


def get_greenhouse_jobs(api_config: dict[str, Any], company_id: int, company_name: str = "") -> list[JobCandidate]:
    return extract_jobs(get_jobs(api_config["url"]), company_id)


def is_greenhouse_job_active(api_url: str | None, job_id: str | None) -> bool:
    """Return whether a Greenhouse posting exists; propagate other failures."""
    if not isinstance(api_url, str) or not api_url:
        raise ValueError("Greenhouse API URL is required")
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("Job ID is required")

    path_parts = urlsplit(api_url).path.strip("/").split("/")
    if len(path_parts) < 3 or path_parts[:2] != ["v1", "boards"]:
        raise ValueError(f"Invalid Greenhouse API URL: {api_url!r}")
    board_token = path_parts[2]
    if not board_token:
        raise ValueError("Greenhouse board token is required")

    url = (
        "https://boards-api.greenhouse.io/v1/boards/"
        f"{quote(board_token.strip(), safe='')}/jobs/{quote(job_id.strip(), safe='')}"
    )
    try:
        response = request_json("GET", url, timeout=10)
    except HTTPResponseError as error:
        if error.status_code == 404:
            return False
        raise
    if not isinstance(response, dict):
        raise ValueError("Greenhouse returned an invalid job response")
    if str(response.get("id")) != job_id.strip():
        raise ValueError("Greenhouse returned a different or invalid job ID")
    return True
