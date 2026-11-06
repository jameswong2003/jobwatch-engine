"""Database-independent checks for whether stored postings remain active."""

import asyncio
from dataclasses import dataclass
from typing import Optional, Sequence

from jobwatch.models.job_types import JobBoardType
from jobwatch.scrapers.greenhouse_util import is_greenhouse_job_active
from jobwatch.scrapers.lever_util import is_lever_job_active
from jobwatch.scrapers.workday_util import is_workday_job_active
from jobwatch.service.scraping import CompanyConfig


@dataclass(frozen=True)
class JobCheckInput:
    """A stored posting identity and the company configuration it belongs to."""

    posting_id: int
    job_id: Optional[str]
    company: CompanyConfig


@dataclass(frozen=True)
class JobActivityError:
    """A posting check failure that should not change its stored active state."""

    posting_id: int
    company_id: int
    company_name: str
    error_message: str


@dataclass(frozen=True)
class _CheckResult:
    posting_id: int
    inactive: bool = False
    error_message: Optional[str] = None


async def check_job_activity(
    postings: Sequence[JobCheckInput],
    max_concurrent_checks: int = 10,
) -> tuple[list[int], list[JobActivityError]]:
    """Return backend posting IDs found inactive and per-posting check errors.

    Unsupported job boards are skipped. Each supported check runs in a worker
    thread with bounded concurrency, and an individual failure does not stop
    the remaining checks.
    """
    if (
        not isinstance(max_concurrent_checks, int)
        or isinstance(max_concurrent_checks, bool)
        or max_concurrent_checks <= 0
    ):
        raise ValueError("max_concurrent_checks must be a positive integer")

    semaphore = asyncio.Semaphore(max_concurrent_checks)

    eligible_postings: list[JobCheckInput] = []
    for posting in postings:
        if posting.company.job_board_type not in {
            JobBoardType.GREENHOUSE,
            JobBoardType.WORKDAY,
            JobBoardType.LEVER,
        }:
            continue
        eligible_postings.append(posting)

    async def check_posting(posting: JobCheckInput) -> _CheckResult:
        company = posting.company
        try:
            async with semaphore:
                if company.job_board_type is JobBoardType.GREENHOUSE:
                    active = await asyncio.to_thread(
                        is_greenhouse_job_active, company.api_url, posting.job_id
                    )
                elif company.job_board_type is JobBoardType.WORKDAY:
                    active = await asyncio.to_thread(
                        is_workday_job_active, company.api_url, posting.job_id
                    )
                else:
                    active = await asyncio.to_thread(
                        is_lever_job_active, company.api_url, posting.job_id
                    )
            return _CheckResult(posting_id=posting.posting_id, inactive=not active)
        except Exception as error:
            return _CheckResult(posting_id=posting.posting_id, error_message=str(error))

    results = await asyncio.gather(
        *(check_posting(posting) for posting in eligible_postings)
    )
    inactive_ids: list[int] = []
    errors: list[JobActivityError] = []
    for posting, result in zip(eligible_postings, results):
        if result.error_message is not None:
            errors.append(
                JobActivityError(
                    posting_id=posting.posting_id,
                    company_id=posting.company.company_id,
                    company_name=posting.company.company_name,
                    error_message=result.error_message,
                )
            )
        elif result.inactive:
            inactive_ids.append(result.posting_id)
    return inactive_ids, errors
