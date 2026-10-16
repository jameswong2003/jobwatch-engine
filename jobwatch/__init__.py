"""Public database-independent JobWatch scraping API."""

from jobwatch.models.job_types import JobBoardType
from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.service.job_activity import (
    JobActivityError,
    JobCheckInput,
    check_job_activity,
)
from jobwatch.service.scraping import CompanyConfig, ScrapeError, process_jobs_from_companies

__all__ = [
    "CompanyConfig",
    "JobBoardType",
    "JobCandidate",
    "JobActivityError",
    "JobCheckInput",
    "ScrapeError",
    "check_job_activity",
    "process_jobs_from_companies",
]
