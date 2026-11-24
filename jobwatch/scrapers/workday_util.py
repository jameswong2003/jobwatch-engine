from datetime import date
from typing import Any
import logging
from urllib.parse import quote, urlsplit, urlunsplit

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json

logger = logging.getLogger(__name__)


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


def get_workday_jobs(api_config: dict[str, Any], company_id: int, company_name: str, company_job_url: str) -> list[JobCandidate]:
    api_url = api_config.get("url")
    if not isinstance(api_url, str) or not api_url.strip():
        raise ValueError("api_config.url must be a non-empty string")
    return extract_jobs(get_jobs(api_url), company_id, company_job_url)


def is_workday_job_active(api_url: str | None, job_path: str | None) -> bool:
    """Return whether a Workday posting is available; failures mark it inactive."""
    try:
        if not isinstance(api_url, str) or not isinstance(job_path, str):
            raise ValueError("Workday API URL and job path are required")
        parsed_url = urlsplit(api_url)
        path = parsed_url.path.rstrip("/")
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or not path.endswith("/jobs")
            or not job_path.startswith("/job/")
        ):
            raise ValueError("Invalid Workday API URL or job path")

        detail_path = f"{path[:-5]}{quote(job_path, safe='/%')}"
        url = urlunsplit((parsed_url.scheme, parsed_url.netloc, detail_path, "", ""))
        response = request_json("GET", url, timeout=10)
        if not isinstance(response, dict) or not isinstance(response.get("jobPostingInfo"), dict):
            raise ValueError("Workday returned an invalid job response")
        return True
    except Exception as error:
        logger.warning(
            "Workday job check failed api_url=%s job_path=%s error=%s",
            api_url,
            job_path,
            error,
        )
        return False
