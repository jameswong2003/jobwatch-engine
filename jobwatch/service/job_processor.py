import asyncio
from typing import Optional

from jobwatch.db.init_db import init_db
from jobwatch.db.company_queries import get_all_companies, get_company_by_id
from jobwatch.db.job_queries import insert_job_list, materialize_new_job_candidates
from jobwatch.db.error_log_queries import insert_error_log_list
from jobwatch.models.Company import Company
from jobwatch.models.ErrorLog import ErrorLog
from jobwatch.service.scraping import CompanyConfig, process_jobs_from_companies


async def process_job_cycle(
    dry_run: bool = False,
    company_id: Optional[int] = None,
    max_concurrent_company_scrapes: Optional[int] = None,
) -> None:
    """Scrape one cycle and persist new jobs and scrape failures."""
    init_db()
    if company_id is None:
        companies: list[Company] = get_all_companies()
    else:
        company = get_company_by_id(company_id)
        if company is None:
            raise ValueError(f"No company found with ID {company_id}")
        companies = [company]

    company_configs = [
        CompanyConfig(
            company_id=company.id,
            company_name=company.company_name,
            company_job_url=company.company_job_url,
            job_board_type=company.job_board_type,
            api_url=company.api_url,
        )
        for company in companies
    ]
    candidates, scrape_errors = await process_jobs_from_companies(
        company_configs, max_concurrent_company_scrapes
    )
    errors = [
        ErrorLog(
            company_id=error.company_id,
            company_name=error.company_name,
            original_api_url=error.original_api_url,
            original_company_job_url=error.original_company_job_url,
            error_message=error.error_message,
            occurred_at=error.occurred_at,
        )
        for error in scrape_errors
    ]
    jobs = await asyncio.to_thread(materialize_new_job_candidates, candidates)

    if dry_run:
        print("\n=== DRY RUN: no DB writes ===")
        print(f"Scraped {len(candidates)} job candidates; {len(jobs)} are not in the database yet.")
        for error in scrape_errors:
            print(f"{error.company_name}: {error.error_message}")
        return

    if errors:
        insert_error_log_list(errors)

    if jobs:
        insert_job_list(jobs)
    print(f"Scraped {len(candidates)} job candidates; stored {len(jobs)} new jobs and {len(errors)} scrape errors.")
