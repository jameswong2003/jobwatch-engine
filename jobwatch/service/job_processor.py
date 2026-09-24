import asyncio
import datetime
from dataclasses import dataclass
from typing import List, Optional, Tuple

from jobwatch.db.init_db import init_db
from jobwatch.db.company_queries import get_all_companies, get_company_by_id
from jobwatch.db.job_queries import insert_job_list, materialize_new_job_candidates
from jobwatch.db.error_log_queries import insert_error_log_list
from jobwatch.helpers.mapper import api_mapper
from jobwatch.models.Company import Company, JobBoardType
from jobwatch.models.Job import Job
from jobwatch.models.job_types import JobCategoryType
from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.models.ErrorLog import ErrorLog
from jobwatch.service.config import EmailConfig
from jobwatch.service.email_client import format_digest_preview, send_job_notifications


MAX_CONCURRENT_COMPANY_SCRAPES = 10


@dataclass(frozen=True)
class _CompanyScrapeInput:
    company_id: int
    company_name: str
    company_job_url: str
    job_board_type: JobBoardType
    has_api: bool
    api_url: Optional[str]


@dataclass
class _CompanyScrapeResult:
    company: _CompanyScrapeInput
    jobs: Optional[List[JobCandidate]] = None
    error_message: Optional[str] = None


async def process_jobs_from_companies(
    companies: List[Company],
) -> Tuple[List[JobCandidate], List[ErrorLog]]:
    company_inputs = [
        _CompanyScrapeInput(
            company_id=company.id,
            company_name=company.company_name,
            company_job_url=company.company_job_url,
            job_board_type=company.job_board_type,
            has_api=company.has_api,
            api_url=company.api_url,
        )
        for company in companies
    ]
    eligible_companies = [
        company for company in company_inputs
        if company.has_api and company.api_url is not None
    ]

    for company in eligible_companies:
        print(f"\nCompany Name: {company.company_name} — searching for new jobs")

    scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_COMPANY_SCRAPES)

    async def scrape_company(company: _CompanyScrapeInput) -> _CompanyScrapeResult:
        try:
            async with scrape_semaphore:
                jobs = await asyncio.to_thread(
                    api_mapper,
                    company.job_board_type,
                    company.company_id,
                    company.company_name,
                    company.api_url,
                    company.company_job_url,
                )
            return _CompanyScrapeResult(company=company, jobs=jobs)
        except Exception as error:
            return _CompanyScrapeResult(company=company, error_message=str(error))

    scrape_results = await asyncio.gather(
        *(scrape_company(company) for company in eligible_companies)
    )

    jobs: List[JobCandidate] = []
    errors: List[ErrorLog] = []
    for result in scrape_results:
        company = result.company
        if result.error_message is not None:
            print(f"Error fetching jobs for {company.company_name}: {result.error_message}")
            errors.append(
                ErrorLog(
                    company_id=company.company_id,
                    company_name=company.company_name,
                    original_api_url=company.api_url,
                    original_company_job_url=company.company_job_url,
                    error_message=result.error_message,
                    occurred_at=datetime.datetime.utcnow(),
                )
            )
            continue

        company_jobs = result.jobs or []
        print(f"Fetched {len(company_jobs)} job candidates for {company.company_name}")
        jobs.extend(company_jobs)

    return jobs, errors


async def job_loop(
    poll_interval_seconds: int,
    email_config: Optional[EmailConfig] = None,
    category_filter: Optional[JobCategoryType] = None,
    dry_run: bool = False,
    company_id: Optional[int] = None,
) -> None:
    """Continuously process jobs, print notifications, and email a digest of new postings."""
    init_db()
    if company_id is None:
        companies: List[Company] = get_all_companies()
    else:
        company = get_company_by_id(company_id)
        if company is None:
            raise ValueError(f"No company found with ID {company_id}")
        companies = [company]

    while True:
        try:
            candidates, errors = await process_jobs_from_companies(companies)
            jobs = await asyncio.to_thread(materialize_new_job_candidates, candidates)

            jobs_to_send = (
                jobs if category_filter is None
                else [job for job in jobs if job.category == category_filter]
            )

            if dry_run:
                # Jobs aren't persisted in dry-run mode, so the `company` relationship
                # (normally lazy-loaded after insert_job_list commits) is never populated.
                # Attach it manually from the already-loaded companies list instead.
                companies_by_id = {company.id: company for company in companies}
                for job in jobs_to_send:
                    job.company = companies_by_id.get(job.company_id)

                subject, text_body = format_digest_preview(jobs_to_send, errors)
                print("\n=== DRY RUN: no DB writes, no email sent ===")
                print(f"Subject: {subject}")
                print(text_body)
                return

            if errors:
                insert_error_log_list(errors)

            if jobs or errors:
                if jobs:
                    insert_job_list(jobs)
                print("***SENDING OUT EMAIL***")
                await asyncio.to_thread(send_job_notifications, jobs_to_send, email_config, errors)
        except Exception as e:
            print(f"job_loop iteration failed: {e}")

        print(f"\nWaiting {poll_interval_seconds} seconds before next check...\n")
        await asyncio.sleep(poll_interval_seconds)
