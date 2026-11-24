import argparse
import asyncio
import json

import pytest
from sqlalchemy import create_engine, inspect, text

from jobwatch import CompanyConfig, JobBoardType, process_jobs_from_companies
from jobwatch.db import init_db
from jobwatch.service import scraping
from jobwatch.helpers import mapper
from jobwatch.scrapers import (
    ashby_util, greenhouse_util, lever_util, oraclecloud_util,
    rippling_util, smartrecruiters_util, workday_util,
)
import manage


def test_scraping_passes_company_and_records_null_error_url(monkeypatch):
    config = {"url": "https://example.com/jobs", "parameters": {"limit": 50}}
    company = CompanyConfig(1, "Example", "https://example.com", "GREENHOUSE", config)
    observed = []

    def scrape(company):
        observed.append(company)
        raise ValueError("request failed")

    monkeypatch.setattr(scraping, "api_mapper", scrape)
    jobs, errors = asyncio.run(process_jobs_from_companies([company]))

    assert observed == [company]
    assert observed[0].api_config is config
    assert jobs == []
    assert len(errors) == 1
    assert errors[0].original_api_url is None
    assert errors[0].error_message == "request failed"


@pytest.mark.parametrize("config", [{}, {"url": None}, {"url": ""}, {"parameters": {"limit": 50}}])
def test_scraping_reports_missing_provider_url(monkeypatch, config):
    def request_json(*args, **kwargs):
        pytest.fail("A missing URL must fail before an HTTP request")

    monkeypatch.setattr(greenhouse_util, "request_json", request_json)
    company = CompanyConfig(1, "Example", "https://example.com", "GREENHOUSE", config)
    jobs, errors = asyncio.run(process_jobs_from_companies([company]))

    assert jobs == []
    assert len(errors) == 1
    assert errors[0].original_api_url is None
    assert errors[0].error_message == "api_config.url must be a non-empty string"


@pytest.mark.parametrize("board, provider", [
    (JobBoardType.ASHBY, "get_ashby_jobs"),
    (JobBoardType.GREENHOUSE, "get_greenhouse_jobs"),
    (JobBoardType.WORKDAY, "get_workday_jobs"),
    (JobBoardType.LEVER, "get_lever_jobs"),
    (JobBoardType.ORACLE, "get_oracle_cloud_jobs"),
    (JobBoardType.SMARTRECRUITERS, "get_smartrecruiters_jobs"),
    (JobBoardType.RIPPLING, "get_rippling_jobs"),
    (JobBoardType.AMAZON, "get_amazon_jobs"),
    (JobBoardType.IBM, "get_ibm_jobs"),
])
def test_mapper_passes_full_configuration_to_provider(monkeypatch, board, provider):
    config = {"parameters": {"limit": 50}}
    observed = []
    monkeypatch.setattr(mapper, provider, lambda *args: observed.append(args) or [])
    company = CompanyConfig(1, "Example", "https://example.com", board, config)
    assert mapper.api_mapper(company) == []
    expected = (config, 1, "Example")
    if board is JobBoardType.ASHBY:
        expected = (company, config)
    if board is JobBoardType.WORKDAY:
        expected += ("https://example.com",)
    assert observed == [expected]


@pytest.mark.parametrize("module, provider, response, method", [
    (greenhouse_util, "get_greenhouse_jobs", {"jobs": []}, "GET"),
    (lever_util, "get_lever_jobs", [], "GET"),
    (oraclecloud_util, "get_oracle_cloud_jobs", {"items": [{"requisitionList": []}]}, "GET"),
    (rippling_util, "get_rippling_jobs", {"items": []}, "GET"),
    (smartrecruiters_util, "get_smartrecruiters_jobs", {"content": []}, "GET"),
    (workday_util, "get_workday_jobs", {"jobPostings": []}, "POST"),
])
def test_provider_reads_url_from_configuration(monkeypatch, module, provider, response, method):
    requests = []

    def request_json(request_method, url, **kwargs):
        requests.append((request_method, url, kwargs))
        return response

    monkeypatch.setattr(module, "request_json", request_json)
    config = {"url": "https://api.example/jobs", "parameters": {"limit": 50}}
    arguments = (config, 1, "Example")
    if module is workday_util:
        arguments += ("https://example.com",)
    assert getattr(module, provider)(*arguments) == []
    assert requests[0][:2] == (method, config["url"])
    assert requests[0][2]["timeout"] == 10
    for invalid_config in ({}, {"url": None}, {"url": ""}, {"url": "   "}):
        with pytest.raises(ValueError, match="api_config.url must be a non-empty string"):
            getattr(module, provider)(invalid_config, *arguments[1:])
    assert len(requests) == 1


def test_ashby_reads_hosted_page_name_from_configuration(monkeypatch):
    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"data": {"jobBoard": {"jobPostings": [
            {"id": "existing-id", "title": "Engineer", "locationName": "Remote"},
        ]}}}

    monkeypatch.setattr(ashby_util, "request_json", request_json)
    config = {"organizationHostedJobsPageName": "hosted-board"}
    company = CompanyConfig(1, "Different Company Name", "https://example.com/careers", "ASHBY", config)
    jobs, errors = asyncio.run(process_jobs_from_companies([company]))

    assert errors == []
    assert len(jobs) == 1
    assert jobs[0].job_id == "existing-id"
    assert jobs[0].job_posting_url == "https://jobs.ashbyhq.com/hosted-board/existing-id"
    assert jobs[0].location == "Remote"
    assert requests[0][:2] == ("POST", ashby_util.API_URL)
    assert requests[0][2]["json"] == {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": "hosted-board"},
        "query": ashby_util.QUERY,
    }
    assert requests[0][2]["timeout"] == 10


def test_standalone_startup_upgrades_existing_company_rows(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE company (id INTEGER PRIMARY KEY, company_name TEXT NOT NULL, company_job_url TEXT NOT NULL, job_board_type TEXT NOT NULL, api_url TEXT, has_api BOOLEAN NOT NULL)"))
        connection.execute(text("INSERT INTO company VALUES (1, 'Example', 'https://example.com', 'GREENHOUSE', 'https://api.example/jobs', 1), (2, 'No URL', 'https://example.org', 'GREENHOUSE', NULL, 0)"))
    monkeypatch.setattr(init_db, "engine", engine)
    try:
        init_db.init_db()
        init_db.init_db()
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT id, api_config FROM company ORDER BY id")).all()
            assert [(row.id, json.loads(row.api_config)) for row in rows] == [(1, {"url": "https://api.example/jobs"}), (2, {})]
            columns = {column["name"] for column in inspect(connection).get_columns("company")}
            assert "api_url" not in columns
            assert "has_api" not in columns
    finally:
        engine.dispose()


def test_standalone_startup_resumes_backfill_and_preserves_config(monkeypatch):
    engine = create_engine("sqlite://")
    configs = [{"parameters": {"unset": None}}, {"url": "https://new.example/jobs", "limit": 50}]
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE company (id INTEGER PRIMARY KEY, company_name TEXT NOT NULL, "
            "company_job_url TEXT NOT NULL, job_board_type TEXT NOT NULL, api_url TEXT, "
            "api_config JSON NOT NULL DEFAULT '{}')"
        ))
        for company_id, config in enumerate(configs, start=1):
            connection.execute(text(
                "INSERT INTO company VALUES (:id, :name, 'https://example.com', 'GREENHOUSE', "
                "'https://old.example/jobs', :config)"
            ), {"id": company_id, "name": f"Company {company_id}", "config": json.dumps(config)})
    monkeypatch.setattr(init_db, "engine", engine)
    try:
        init_db.init_db()
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT api_config FROM company ORDER BY id")).scalars().all()
        assert [json.loads(config) for config in rows] == [
            {**configs[0], "url": "https://old.example/jobs"}, configs[1],
        ]
    finally:
        engine.dispose()


def test_manage_parses_json_objects_and_rejects_retired_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["manage.py", "add", "--name", "Example", "--job-url", "https://example.com", "--board-type", "GREENHOUSE", "--api-config", '{"url":"https://api.example/jobs","limit":50}'])
    assert manage.parse_args().api_config == {"url": "https://api.example/jobs", "limit": 50}
    monkeypatch.setattr("sys.argv", ["manage.py", "update", "--name", "Example", "--api-url", "https://api.example/jobs"])
    with pytest.raises(SystemExit):
        manage.parse_args()


@pytest.mark.parametrize("value", ["null", "[]", '"https://api.example/jobs"', '{"url":5}', '{"url":""}', "invalid"])
def test_manage_rejects_invalid_configuration(value):
    with pytest.raises(argparse.ArgumentTypeError):
        manage._parse_api_config(value)


def test_manage_import_preserves_extra_keys_and_rejects_old_shape(tmp_path):
    record = {"id": 1, "company_name": "Example", "company_job_url": "https://example.com", "job_board_type": "GREENHOUSE", "api_config": {"url": "https://api.example/jobs", "parameters": {"limit": 50}}}
    path = tmp_path / "companies.json"
    path.write_text(json.dumps([record]))
    assert manage._load_companies_file(str(path))[0]["api_config"] == record["api_config"]
    record["api_url"] = record.pop("api_config")["url"]
    path.write_text(json.dumps([record]))
    with pytest.raises(ValueError):
        manage._load_companies_file(str(path))
