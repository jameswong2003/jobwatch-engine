"""Database-independent public API for scraping configured companies."""

import asyncio
import datetime
from dataclasses import dataclass
from typing import Optional, Sequence

from jobwatch.helpers.mapper import api_mapper
from jobwatch.models.job_types import JobBoardType
from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.service.config import load_max_concurrent_company_scrapes


@dataclass(frozen=True)
class CompanyConfig:
    """Plain configuration needed to scrape one company's job board."""

    company_id: int
    company_name: str
    company_job_url: str
    job_board_type: JobBoardType | str
    has_api: bool
    api_url: Optional[str]

    def __post_init__(self) -> None:
        if isinstance(self.job_board_type, str):
            try:
                object.__setattr__(self, "job_board_type", JobBoardType(self.job_board_type))
            except ValueError:
                try:
                    object.__setattr__(self, "job_board_type", JobBoardType[self.job_board_type])
                except KeyError:
                    raise ValueError(f"Unknown job board type: {self.job_board_type!r}") from None


@dataclass(frozen=True)
class ScrapeError:
    """A company-level scrape failure, independent of any persistence model."""

    company_id: int
    company_name: str
    original_api_url: Optional[str]
    original_company_job_url: str
    error_message: str
    occurred_at: datetime.datetime


@dataclass(frozen=True)
class _CompanyScrapeResult:
    company: CompanyConfig
    jobs: Optional[list[JobCandidate]] = None
    error_message: Optional[str] = None


async def process_jobs_from_companies(
    companies: Sequence[CompanyConfig],
    max_concurrent_company_scrapes: Optional[int] = None,
) -> tuple[list[JobCandidate], list[ScrapeError]]:
    """Scrape all eligible companies and return every normalized posting.

    This function does not access a database or filter postings by newness. The
    caller owns deduplication and persistence. Companies without an enabled API
    URL are skipped, while one company's scrape failure is returned as a
    ``ScrapeError`` without preventing other companies from completing.
    """
    concurrency = (
        load_max_concurrent_company_scrapes()
        if max_concurrent_company_scrapes is None
        else max_concurrent_company_scrapes
    )
    if not isinstance(concurrency, int) or isinstance(concurrency, bool) or concurrency <= 0:
        raise ValueError("max_concurrent_company_scrapes must be a positive integer")
    scrape_semaphore = asyncio.Semaphore(concurrency)
    eligible_companies = [
        company for company in companies if company.has_api and company.api_url
    ]

    async def scrape_company(company: CompanyConfig) -> _CompanyScrapeResult:
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

    results = await asyncio.gather(*(scrape_company(company) for company in eligible_companies))
    jobs: list[JobCandidate] = []
    errors: list[ScrapeError] = []
    for result in results:
        company = result.company
        if result.error_message is not None:
            errors.append(
                ScrapeError(
                    company_id=company.company_id,
                    company_name=company.company_name,
                    original_api_url=company.api_url,
                    original_company_job_url=company.company_job_url,
                    error_message=result.error_message,
                    occurred_at=datetime.datetime.utcnow(),
                )
            )
        else:
            jobs.extend(result.jobs or [])
    return jobs, errors
