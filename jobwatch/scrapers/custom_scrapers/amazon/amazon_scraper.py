from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin


from jobwatch.db import company_queries, job_queries
from jobwatch.models.Job import Job
from jobwatch.scrapers.client import request_json


API_URL = "https://www.amazon.jobs/en/search.json"
API_PARAMS = {
    "offset": 0,
    "result_limit": 20,
    "sort": "recent",
    "country": "USA",
}
AMAZON_JOBS_BASE_URL = "https://www.amazon.jobs"


def get_jobs() -> dict[str, Any]:
    """Fetch one page of recent Amazon jobs in the USA."""
    data = request_json(
        "GET",
        API_URL,
        params=API_PARAMS,
        headers={"Accept-Encoding": "identity"},
        timeout=10,
    )

    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("Amazon jobs API response must contain a jobs list")
    return data


def _posted_date(value: Any) -> date:
    """Parse Amazon's human-readable posted date, accepting ISO dates as well."""
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


def extract_new_jobs(json_data: dict[str, Any], company_name: str) -> list[Job]:
    """Map Amazon search results to new jobs, using one batched URL lookup."""
    if not isinstance(json_data, dict) or not isinstance(json_data.get("jobs"), list):
        raise ValueError("Amazon jobs data must contain a jobs list")

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        return []

    postings = [posting for posting in json_data["jobs"] if isinstance(posting, dict)]
    url_by_posting: list[tuple[dict[str, Any], str]] = []
    for posting in postings:
        path = posting.get("job_path")
        if not isinstance(path, str) or not path.strip():
            path = posting.get("url_next_step")
        if isinstance(path, str) and path.strip():
            url_by_posting.append((posting, urljoin(AMAZON_JOBS_BASE_URL, path.strip())))

    candidate_urls = list(dict.fromkeys(url for _, url in url_by_posting))
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    new_jobs: list[Job] = []
    seen_urls: set[str] = set()
    for posting, job_url in url_by_posting:
        if job_url in existing_urls or job_url in seen_urls:
            continue

        raw_id = posting.get("id_icims") or posting.get("id")
        job_id = str(raw_id).strip() if raw_id is not None else ""
        title = posting.get("title")
        if not job_id or not isinstance(title, str) or not title.strip():
            continue

        new_jobs.append(
            Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job_id,
                job_date=_posted_date(posting.get("posted_date")),
                job_title=title.strip(),
                active=True,
                location=posting.get("location") if isinstance(posting.get("location"), str) else "Unknown Location",
                date_added=date.today(),
            )
        )
        seen_urls.add(job_url)

    return new_jobs


def get_amazon_jobs(company_name: str) -> list[Job]:
    """Fetch and extract recent Amazon jobs for the named company."""
    return extract_new_jobs(get_jobs(), company_name)
