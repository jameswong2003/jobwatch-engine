from datetime import date as date_
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from jobwatch.db.database import Base
from jobwatch.models.Company import Company
from jobwatch.models.job_types import JobCategoryType

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    job_posting_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    job_date: Mapped[date_] = mapped_column(Date, nullable=False)
    job_title: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_added: Mapped[date_] = mapped_column(Date, nullable=False)
    category: Mapped[Optional[JobCategoryType]] = mapped_column(
        Enum(JobCategoryType, name="job_category_enum"), nullable=True
    )

    company: Mapped[Company] = relationship("Company", backref="jobs")
