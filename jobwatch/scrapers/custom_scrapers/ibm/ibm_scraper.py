from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlsplit

from jobwatch.scrapers.client import request_json
from jobwatch.scrapers.job_candidate import JobCandidate

API_URL = "https://www-api.ibm.com/search/api/v2"
# shortcut: fetches the latest 30 worldwide postings, add pagination when full coverage is required.
API_PAYLOAD = {
    "appId": "careers",
    "scopes": ["careers2"],
    "query": {"bool": {"must": []}},
    "aggs": {
        "field_keyword_172": {
            "filter": {"match_all": {}},
            "aggs": {
                "field_keyword_17": {"terms": {"field": "field_keyword_17", "size": 6}},
                "field_keyword_17_count": {"cardinality": {"field": "field_keyword_17"}},
            },
        },
        "field_keyword_083": {
            "filter": {"match_all": {}},
            "aggs": {
                "field_keyword_08": {"terms": {"field": "field_keyword_08", "size": 6}},
                "field_keyword_08_count": {"cardinality": {"field": "field_keyword_08"}},
            },
        },
        "field_keyword_184": {
            "filter": {"match_all": {}},
            "aggs": {
                "field_keyword_18": {"terms": {"field": "field_keyword_18", "size": 6}},
                "field_keyword_18_count": {"cardinality": {"field": "field_keyword_18"}},
            },
        },
        "field_keyword_055": {
            "filter": {"match_all": {}},
            "aggs": {
                "field_keyword_05": {"terms": {"field": "field_keyword_05", "size": 1000}},
                "field_keyword_05_count": {"cardinality": {"field": "field_keyword_05"}},
            },
        },
    },
    "size": 30,
    "sort": [{"dcdate": "desc"}, {"_score": "desc"}],
    "lang": "zz",
    "localeSelector": {},
    "sm": {"query": "", "lang": "zz"},
    "_source": [
        "_id", "title", "url", "description", "language", "entitled",
        "field_keyword_17", "field_keyword_08", "field_keyword_18", "field_keyword_19",
    ],
}


def get_jobs() -> dict[str, Any]:
    return request_json(
        "POST", API_URL, json=API_PAYLOAD,
        headers={"Content-Type": "application/json"}, timeout=10,
    )


def _posted_date(value: Any) -> date:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date()
        except (ValueError, OverflowError, OSError):
            pass
    return date.today()


def extract_jobs(json_data: dict[str, Any], company_id: int) -> list[JobCandidate]:
    hits = json_data.get("hits") if isinstance(json_data, dict) else None
    if not isinstance(hits, dict) or not isinstance(hits.get("hits"), list):
        raise ValueError("IBM jobs API response must contain a hits.hits list")
    candidates: list[JobCandidate] = []
    seen_urls: set[str] = set()
    for posting in hits["hits"]:
        if not isinstance(posting, dict) or not isinstance(posting.get("_source"), dict):
            continue
        source = posting["_source"]
        title, job_url = source.get("title"), source.get("url")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(job_url, str) or not job_url.strip():
            continue
        job_url = job_url.strip()
        try:
            parsed_url = urlsplit(job_url)
            if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                continue
            job_id = parse_qs(parsed_url.query).get("jobId", [""])[0].strip()
        except ValueError:
            continue
        if job_url in seen_urls:
            continue
        raw_id = posting.get("_id")
        if not job_id:
            job_id = str(raw_id).strip() if raw_id is not None else ""
        sort = posting.get("sort")
        timestamp = sort[0] if isinstance(sort, list) and sort else None
        location = source.get("field_keyword_19")
        candidates.append(JobCandidate(
            company_id=company_id, job_posting_url=job_url, job_id=job_id,
            job_date=_posted_date(timestamp), job_title=title.strip(), active=True,
            location=location if isinstance(location, str) and location.strip() else "Unknown Location",
            date_added=date.today(),
        ))
        seen_urls.add(job_url)
    return candidates


def get_ibm_jobs(company_id: int, company_name: str = "") -> list[JobCandidate]:
    return extract_jobs(get_jobs(), company_id)
