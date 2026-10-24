import asyncio
import threading
import time

import pytest

from jobwatch import CompanyConfig, JobBoardType, JobCheckInput, check_job_activity
from jobwatch.scrapers import client, greenhouse_util, workday_util
from jobwatch.scrapers.client import HTTPResponseError


def _company(
    board_type=JobBoardType.GREENHOUSE,
    api_url="https://boards-api.greenhouse.io/v1/boards/twilio/jobs?content=true",
):
    return CompanyConfig(
        company_id=7,
        company_name="Twilio",
        company_job_url="https://twilio.com/careers",
        job_board_type=board_type,
        api_url=api_url,
    )


def _unexpected_request(*args, **kwargs):
    raise AssertionError("request should not be made")


def test_greenhouse_activity_uses_company_api_url_and_job_id(monkeypatch):
    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"id": 8164465, "title": "Engineer"}

    monkeypatch.setattr(greenhouse_util, "request_json", request_json)

    assert greenhouse_util.is_greenhouse_job_active(
        "https://boards-api.greenhouse.io/v1/boards/twilio/jobs?content=true", "8164465"
    )
    assert requests == [
        (
            "GET",
            "https://boards-api.greenhouse.io/v1/boards/twilio/jobs/8164465",
            {"timeout": 10},
        )
    ]


def test_greenhouse_activity_treats_any_404_as_inactive(monkeypatch):
    def request_json(*args, **kwargs):
        raise HTTPResponseError("Error 404: anything", 404)

    monkeypatch.setattr(greenhouse_util, "request_json", request_json)

    assert greenhouse_util.is_greenhouse_job_active(
        "https://boards-api.greenhouse.io/v1/boards/twilio/jobs", "8164465"
    ) is False


def test_request_json_preserves_http_status_code(monkeypatch):
    class NotFoundResponse:
        status_code = 404
        text = '{"error":"Job not found"}'
        reason = "Not Found"
        ok = False

    monkeypatch.setattr(
        client._CurlSession,
        "send",
        lambda *args, **kwargs: NotFoundResponse(),
    )

    with pytest.raises(HTTPResponseError) as error:
        client.request_json("GET", "https://boards-api.greenhouse.io/job")

    assert error.value.status_code == 404


def test_greenhouse_activity_rejects_malformed_success_response(monkeypatch):
    monkeypatch.setattr(greenhouse_util, "request_json", lambda *args, **kwargs: {})

    with pytest.raises(ValueError, match="different or invalid job ID"):
        greenhouse_util.is_greenhouse_job_active(
            "https://boards-api.greenhouse.io/v1/boards/twilio/jobs", "8164465"
        )


def test_workday_activity_builds_detail_url_from_company_api_and_external_path(monkeypatch):
    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"jobPostingInfo": {"title": "Engineer"}}

    monkeypatch.setattr(workday_util, "request_json", request_json)

    assert workday_util.is_workday_job_active(
        "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs/?x=1",
        "/job/California---San-Francisco/Full-Stack-Software-Engineer---MTS---SMTS_JR253369",
    )
    assert requests == [
        (
            "GET",
            "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/job/California---San-Francisco/Full-Stack-Software-Engineer---MTS---SMTS_JR253369",
            {"timeout": 10},
        )
    ]


def test_workday_activity_preserves_encoded_path_and_marks_bad_responses_inactive(monkeypatch):
    requests = []

    def request_json(method, url, **kwargs):
        requests.append(url)
        return {"jobPostingInfo": "invalid"}

    monkeypatch.setattr(workday_util, "request_json", request_json)

    assert workday_util.is_workday_job_active(
        "https://example.wd1.myworkdayjobs.com/wday/cxs/example/External/jobs",
        "/job/Some%20City/Engineer_JR1",
    ) is False
    assert requests == [
        "https://example.wd1.myworkdayjobs.com/wday/cxs/example/External/job/Some%20City/Engineer_JR1"
    ]


@pytest.mark.parametrize(
    "failure",
    [HTTPResponseError("forbidden", 403), HTTPResponseError("not found", 404), ValueError("network or JSON error")],
)
def test_workday_activity_treats_any_check_error_as_inactive(monkeypatch, failure, caplog):
    monkeypatch.setattr(
        workday_util,
        "request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(failure),
    )

    assert workday_util.is_workday_job_active(
        "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External/jobs",
        "/job/somewhere/Engineer_JR1",
    ) is False
    assert "Workday job check failed" in caplog.text


def test_workday_activity_marks_invalid_config_or_path_inactive_without_request(monkeypatch, caplog):
    monkeypatch.setattr(workday_util, "request_json", _unexpected_request)

    assert workday_util.is_workday_job_active(None, "/job/somewhere/Engineer") is False
    assert workday_util.is_workday_job_active(
        "https://example.com/jobs", "https://evil.example/job/Engineer"
    ) is False
    assert "Invalid Workday API URL or job path" in caplog.text


def test_check_job_activity_returns_inactive_ids_errors_and_skips_other_boards(
    monkeypatch,
):
    def check(api_url, job_id):
        if job_id == "missing":
            return False
        if job_id == "broken":
            raise ValueError("temporary failure")
        return True

    monkeypatch.setattr("jobwatch.service.job_activity.is_greenhouse_job_active", check)
    greenhouse = _company()
    postings = [
        JobCheckInput(posting_id=101, job_id="active", company=greenhouse),
        JobCheckInput(posting_id=102, job_id="missing", company=greenhouse),
        JobCheckInput(posting_id=103, job_id="broken", company=greenhouse),
        JobCheckInput(posting_id=104, job_id="other", company=_company(JobBoardType.LEVER)),
    ]

    inactive_ids, errors = asyncio.run(check_job_activity(postings))

    assert inactive_ids == [102]
    assert [(error.posting_id, error.error_message) for error in errors] == [
        (103, "temporary failure")
    ]


def test_check_job_activity_dispatches_workday_and_preserves_greenhouse_policy(monkeypatch):
    def greenhouse_check(api_url, job_id):
        raise HTTPResponseError("Error 403", 403)

    monkeypatch.setattr("jobwatch.service.job_activity.is_greenhouse_job_active", greenhouse_check)
    monkeypatch.setattr("jobwatch.service.job_activity.is_workday_job_active", lambda *args: False)
    workday = _company(
        JobBoardType.WORKDAY,
        "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External/jobs",
    )

    inactive_ids, errors = asyncio.run(
        check_job_activity(
            [
                JobCheckInput(201, "8164465", _company()),
                JobCheckInput(202, "/job/sf/Engineer_JR1", workday),
            ]
        )
    )

    assert inactive_ids == [202]
    assert [error.posting_id for error in errors] == [201]


def test_check_job_activity_reports_missing_job_id(monkeypatch):
    monkeypatch.setattr(
        greenhouse_util,
        "request_json",
        _unexpected_request,
    )

    inactive_ids, errors = asyncio.run(
        check_job_activity(
            [JobCheckInput(posting_id=101, job_id=None, company=_company())]
        )
    )

    assert inactive_ids == []
    assert errors[0].posting_id == 101
    assert errors[0].error_message == "Job ID is required"


def test_check_job_activity_reports_invalid_greenhouse_api_url(monkeypatch):
    monkeypatch.setattr(
        greenhouse_util,
        "request_json",
        _unexpected_request,
    )

    inactive_ids, errors = asyncio.run(
        check_job_activity(
            [
                JobCheckInput(
                    posting_id=101,
                    job_id="8164465",
                    company=_company(api_url="https://example.com/jobs"),
                )
            ]
        )
    )

    assert inactive_ids == []
    assert errors[0].posting_id == 101
    assert "Invalid Greenhouse API URL" in errors[0].error_message


def test_check_job_activity_reports_missing_greenhouse_api_url(monkeypatch):
    monkeypatch.setattr(greenhouse_util, "request_json", _unexpected_request)

    inactive_ids, errors = asyncio.run(
        check_job_activity(
            [JobCheckInput(posting_id=101, job_id="8164465", company=_company(api_url=None))]
        )
    )

    assert inactive_ids == []
    assert errors[0].posting_id == 101
    assert errors[0].error_message == "Greenhouse API URL is required"


def test_check_job_activity_keeps_non_404_failures_as_errors(monkeypatch):
    def fail_with_server_error(*args, **kwargs):
        raise HTTPResponseError("Error 500: unavailable", 500)

    monkeypatch.setattr(greenhouse_util, "request_json", fail_with_server_error)

    inactive_ids, errors = asyncio.run(
        check_job_activity(
            [JobCheckInput(posting_id=101, job_id="8164465", company=_company())]
        )
    )

    assert inactive_ids == []
    assert errors[0].posting_id == 101
    assert "Error 500" in errors[0].error_message


def test_check_job_activity_accepts_empty_input():
    assert asyncio.run(check_job_activity([])) == ([], [])


def test_check_job_activity_bounds_concurrency(monkeypatch):
    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def check(api_url, job_id):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return True

    monkeypatch.setattr("jobwatch.service.job_activity.is_greenhouse_job_active", check)
    postings = [
        JobCheckInput(posting_id=posting_id, job_id=str(posting_id), company=_company())
        for posting_id in range(5)
    ]

    inactive_ids, errors = asyncio.run(
        check_job_activity(postings, max_concurrent_checks=2)
    )

    assert inactive_ids == []
    assert errors == []
    assert maximum_active == 2
