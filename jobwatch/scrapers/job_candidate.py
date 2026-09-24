"""Database-independent job data returned by scraper implementations."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from jobwatch.models.job_types import JobCategoryType


@dataclass
class JobCandidate:
    company_id: int
    job_posting_url: str
    job_id: str
    job_date: date
    job_title: str
    active: Optional[bool] = True
    location: Optional[str] = None
    date_added: Optional[date] = None
    category: Optional[JobCategoryType] = None
