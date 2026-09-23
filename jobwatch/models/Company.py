import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from jobwatch.db.database import Base

class JobBoardType(enum.Enum):
    ASHBY = "Ashby"
    GREENHOUSE = "Greenhouse"
    WORKDAY = "Workday"
    LEVER = "Lever"
    ORACLE = "Oracle"
    SMARTRECRUITERS = "SmartRecruiters"
    RIPPLING = "Rippling"
    CUSTOM = "Custom"
    AMAZON = "Amazon"
    OTHER = "Other"

class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    company_job_url: Mapped[str] = mapped_column(Text, nullable=False)
    job_board_type: Mapped[JobBoardType] = mapped_column(Enum(JobBoardType, name="job_board_enum"), nullable=False)
    has_api: Mapped[bool] = mapped_column(Boolean, nullable=False)
    api_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
