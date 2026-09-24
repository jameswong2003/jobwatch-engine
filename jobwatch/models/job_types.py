"""Shared enum types that do not depend on the database layer."""

import enum


class JobCategoryType(enum.Enum):
    SOFTWARE = "SOFTWARE"
    HARDWARE = "HARDWARE"
    FINANCE = "FINANCE"
    DATA_SCIENCE = "DATA_SCIENCE"
    PRODUCT = "PRODUCT"
    DESIGN = "DESIGN/UX"
    MARKETING = "MARKETING"
    SALES = "SALES"
    OPERATIONS = "OPERATIONS"
    HUMAN_RESOURCES = "HUMAN_RESOURCES"
    LEGAL = "LEGAL"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    ENGINEERING = "ENGINEERING"
    MEDICAL = "MEDICAL"
    EDUCATION = "EDUCATION"
    OTHER = "Other"


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
