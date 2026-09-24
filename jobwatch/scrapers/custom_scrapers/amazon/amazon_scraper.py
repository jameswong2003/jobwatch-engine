from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json

API_URL = "https://www.amazon.jobs/en/search.json"
API_PARAMS = {"offset": 0, "result_limit": 20, "sort": "recent", "country": "USA"}
AMAZON_JOBS_BASE_URL = "https://www.amazon.jobs"


def get_jobs() -> dict[str, Any]:
    data = request_json("GET", API_URL, params=API_PARAMS, headers={"Accept-Encoding": "identity"}, timeout=10)
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("Amazon jobs API response must contain a jobs list")
    return data


def _posted_date(value: Any) -> date:
    if not isinstance(value, str) or not value.strip():
        return date.today()
    value = value.strip()
    for date_format in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return date.today()


def extract_jobs(json_data: dict[str, Any], company_id: int) -> list[JobCandidate]:
    if not isinstance(json_data, dict) or not isinstance(json_data.get("jobs"), list):
        raise ValueError("Amazon jobs data must contain a jobs list")
    candidates: list[JobCandidate] = []
    seen_urls: set[str] = set()
    for posting in json_data["jobs"]:
        if not isinstance(posting, dict):
            continue
        path = posting.get("job_path")
        if not isinstance(path, str) or not path.strip():
            path = posting.get("url_next_step")
        if not isinstance(path, str) or not path.strip():
            continue
        job_url = urljoin(AMAZON_JOBS_BASE_URL, path.strip())
        raw_id = posting.get("id_icims") or posting.get("id")
        job_id = str(raw_id).strip() if raw_id is not None else ""
        title = posting.get("title")
        if job_url in seen_urls or not isinstance(title, str) or not title.strip():
            continue
        candidates.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=job_id,
            job_date=_posted_date(posting.get("posted_date")), job_title=title.strip(), active=True,
            location=posting.get("location") if isinstance(posting.get("location"), str) else "Unknown Location",
            date_added=date.today(),
        ))
        seen_urls.add(job_url)
    return candidates


def get_amazon_jobs(company_id: int, company_name: str = "") -> list[JobCandidate]:
    return extract_jobs(get_jobs(), company_id)
