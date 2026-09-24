from jobwatch.models.job_types import JobBoardType
from jobwatch.helpers.job_sorter import categorize_jobs
from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.ashby_util import get_ashby_jobs
from jobwatch.scrapers.greenhouse_util import get_greenhouse_jobs
from jobwatch.scrapers.lever_util import get_lever_jobs
from jobwatch.scrapers.oraclecloud_util import get_oracle_cloud_jobs
from jobwatch.scrapers.rippling_util import get_rippling_jobs
from jobwatch.scrapers.smartrecruiters_util import get_smartrecruiters_jobs
from jobwatch.scrapers.workday_util import get_workday_jobs
from jobwatch.scrapers.custom_scrapers.amazon.amazon_scraper import get_amazon_jobs


def api_mapper(
    job_board_type: JobBoardType,
    company_id: int,
    company_name: str,
    api_url: str,
    company_job_url: str,
) -> list[JobCandidate]:
    """Scrape and normalize postings without consulting persistence."""
    match job_board_type:
        case JobBoardType.ASHBY:
            candidates = get_ashby_jobs(api_url, company_id, company_name)
        case JobBoardType.GREENHOUSE:
            candidates = get_greenhouse_jobs(api_url, company_id, company_name)
        case JobBoardType.WORKDAY:
            if not isinstance(company_job_url, str) or not company_job_url.strip():
                raise ValueError(f"Workday company {company_name!r} requires a non-empty company_job_url")
            candidates = get_workday_jobs(api_url, company_id, company_name, company_job_url)
        case JobBoardType.LEVER:
            candidates = get_lever_jobs(api_url, company_id, company_name)
        case JobBoardType.ORACLE:
            candidates = get_oracle_cloud_jobs(api_url, company_id, company_name)
        case JobBoardType.SMARTRECRUITERS:
            candidates = get_smartrecruiters_jobs(api_url, company_id, company_name)
        case JobBoardType.RIPPLING:
            candidates = get_rippling_jobs(api_url, company_id, company_name)
        case JobBoardType.AMAZON:
            candidates = get_amazon_jobs(company_id, company_name)
        case _:
            candidates = []
    return categorize_jobs(candidates)
