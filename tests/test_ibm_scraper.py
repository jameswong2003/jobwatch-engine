import asyncio
from datetime import date

import pytest

from jobwatch import CompanyConfig, JobBoardType, process_jobs_from_companies
from jobwatch.scrapers.custom_scrapers.ibm import ibm_scraper


def posting(job_id="137127", **overrides):
    return {
        "_id": "search-hit-id",
        "_source": {
            "title": " Software Engineer ",
            "url": f"https://careers.ibm.com/careers/JobDetail?jobId={job_id}",
            "field_keyword_19": "Multiple Cities",
        },
        "sort": [1794700800000, 0],
        **overrides,
    }


def test_extract_jobs_maps_fields_and_deduplicates_urls():
    jobs = ibm_scraper.extract_jobs({"hits": {"hits": [
        posting(), posting(), posting("142862"), None, {},
        posting(_source={"title": "", "url": "https://example.test"}),
        posting(_source={"title": "Engineer", "url": "invalid"}),
    ]}}, 42)

    assert len(jobs) == 2
    assert [job.job_id for job in jobs] == ["137127", "142862"]
    job = jobs[0]
    assert job.company_id == 42
    assert job.job_title == "Software Engineer"
    assert job.job_posting_url.endswith("jobId=137127")
    assert job.location == "Multiple Cities"
    assert job.job_date == date(2026, 11, 15)
    assert job.date_added == date.today()
    assert job.active is True


@pytest.mark.parametrize("sort", [None, [], ["invalid"], [True], [float("inf")]])
def test_extract_jobs_uses_fallback_fields(sort):
    job = ibm_scraper.extract_jobs({"hits": {"hits": [posting(
        _source={"title": "Engineer", "url": "https://careers.ibm.com/job"},
        sort=sort,
    )]}}, 42)[0]

    assert job.job_id == "search-hit-id"
    assert job.job_date == date.today()
    assert job.location == "Unknown Location"


@pytest.mark.parametrize("payload", [None, {}, {"hits": []}, {"hits": {}}, {"hits": {"hits": {}}}])
def test_extract_jobs_rejects_malformed_envelope(payload):
    with pytest.raises(ValueError, match=r"hits.hits list"):
        ibm_scraper.extract_jobs(payload, 42)


def test_extract_jobs_accepts_empty_results():
    assert ibm_scraper.extract_jobs({"hits": {"hits": []}}, 42) == []


def test_ibm_public_scrape_posts_payload_and_categorizes(monkeypatch):
    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"hits": {"hits": [posting()]}, "aggregations": {"ignored": True}}

    monkeypatch.setattr(ibm_scraper, "request_json", request_json)
    company = CompanyConfig(42, "IBM", "https://careers.ibm.com", "IBM", ibm_scraper.API_URL)
    jobs, errors = asyncio.run(process_jobs_from_companies([company]))

    assert errors == []
    assert len(jobs) == 1
    assert jobs[0].category is not None
    assert company.job_board_type is JobBoardType.IBM
    method, url, kwargs = requests[0]
    assert (method, url) == ("POST", "https://www-api.ibm.com/search/api/v2")
    assert kwargs["timeout"] == 10
    assert kwargs["headers"] == {"Content-Type": "application/json"}
    payload = kwargs["json"]
    assert payload["appId"] == "careers"
    assert payload["scopes"] == ["careers2"]
    assert payload["size"] == 30
    assert payload["query"] == {"bool": {"must": []}}
    assert payload["sort"] == [{"dcdate": "desc"}, {"_score": "desc"}]


@pytest.mark.parametrize("failure", [ValueError("HTTP failed"), {"hits": {}}])
def test_ibm_public_scrape_reports_company_error(monkeypatch, failure):
    def request_json(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(ibm_scraper, "request_json", request_json)
    company = CompanyConfig(42, "IBM", "https://careers.ibm.com", JobBoardType.IBM, ibm_scraper.API_URL)
    jobs, errors = asyncio.run(process_jobs_from_companies([company]))

    assert jobs == []
    assert len(errors) == 1
    assert errors[0].company_id == 42
    assert errors[0].error_message
