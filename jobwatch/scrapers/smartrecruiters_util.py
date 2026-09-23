from datetime import date, datetime, timezone

from typing import List, Dict
from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json

"""
Utility functions for interacting with the SmartRecruiters API.
API URL is as follows:
GET https://api.smartrecruiters.com/v1/companies/{JOB_BOARD_NAME}/postings?limit=50

Job posting URL is as follows:
https://jobs.smartrecruiters.com/oneclick-ui/company/{JOB_BOARD_NAME}/publication/{UUID}

Please Note: JOB_BOARD_NAME is case-sensitive. So when adding companies, we should be awared of the cases in the company name under smartrecruiters

limit max is 100
"""

def get_jobs(api_url: str) -> Dict:
    return request_json("GET", api_url, timeout=10)

def extract_new_jobs(json_data: Dict, company_name: str) -> List[Job]:
    jobs_data = json_data.get("content", [])
    jobs: List[Job] = []

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        return []

    candidate_urls = [
        f"https://jobs.smartrecruiters.com/oneclick-ui/company/{company_name}/publication/{job.get('uuid')}"
        for job in jobs_data
    ]
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    for job in jobs_data:
        job_id = job.get("uuid")
        job_url = f"https://jobs.smartrecruiters.com/oneclick-ui/company/{company_name}/publication/{job_id}"

        job_date = datetime.fromisoformat(job.get("releasedDate").replace("Z", "+00:00")).date()

        if job_url and job_url not in existing_urls:
            job_instance = Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job_id,
                job_date=job_date,
                job_title=job.get("name"),
                active=True,
                location=job.get("location").get("fullLocation"),
                date_added=date.today()
            )
            jobs.append(job_instance)
    return jobs

def get_smartrecruiters_jobs(api_url: str, company_name: str) -> List[Job]:
    """
    Fetch and extract new jobs from SmartRecruiters API for a specific company.

    Args:
        api_url (str): The SmartRecruiters API URL for job listings.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        List[Job]: A list of new Job instances not yet in the database.
    """
    raw_jobs = get_jobs(api_url)
    return extract_new_jobs(raw_jobs, company_name)
