"""Public database-independent JobWatch scraping API."""

from jobwatch.models.job_types import JobBoardType
from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.service.scraping import CompanyConfig, ScrapeError, process_jobs_from_companies

__all__ = [
    "CompanyConfig",
    "JobBoardType",
    "JobCandidate",
    "ScrapeError",
    "process_jobs_from_companies",
]
