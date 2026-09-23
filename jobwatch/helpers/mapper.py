from typing import List

from jobwatch.models.Job import Job
from jobwatch.models.Company import JobBoardType
from jobwatch.scrapers.ashby_util import get_ashby_jobs
from jobwatch.scrapers.greenhouse_util import get_greenhouse_jobs
from jobwatch.scrapers.lever_util import get_lever_jobs
from jobwatch.scrapers.oraclecloud_util import get_oracle_cloud_jobs
from jobwatch.scrapers.rippling_util import get_rippling_jobs
from jobwatch.scrapers.smartrecruiters_util import get_smartrecruiters_jobs
from jobwatch.scrapers.workday_util import get_workday_jobs
from jobwatch.scrapers.custom_scrapers.amazon.amazon_scraper import get_amazon_jobs


def api_mapper(job_board_type: JobBoardType, company_name: str, api_url: str) -> List[Job]:
    match job_board_type:
        case JobBoardType.ASHBY:
            return get_ashby_jobs(api_url, company_name)
        case JobBoardType.GREENHOUSE:
            return get_greenhouse_jobs(api_url, company_name)
        case JobBoardType.WORKDAY:
            return get_workday_jobs(api_url, company_name)
        case JobBoardType.LEVER:
            return get_lever_jobs(api_url, company_name)
        case JobBoardType.ORACLE:
            return get_oracle_cloud_jobs(api_url, company_name)
        case JobBoardType.SMARTRECRUITERS:
            return get_smartrecruiters_jobs(api_url, company_name)
        case JobBoardType.RIPPLING:
            return get_rippling_jobs(api_url, company_name)
        case JobBoardType.AMAZON:
            return get_amazon_jobs(company_name)
        case _:
            return []
