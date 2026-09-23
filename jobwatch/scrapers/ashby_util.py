from datetime import datetime, date

from typing import List
from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json

"""
Utility functions for interacting with the Ashby API.
API URL is as follows:
GET https://api.ashbyhq.com/posting-api/job-board/{JOB_BOARD_NAME}?includeCompensation=true
"""

def get_jobs(api_url: str) -> dict:
    """
    Fetch raw job data from the Ashby API for a specific job board.
    """
    return request_json("GET", api_url, timeout=10)

def extract_new_jobs(json_data: dict, company_name: str) -> List[Job]:
    """
    Extracts job objects from Ashby API JSON data, only if they are not already in the database.

    Args:
        json_data (dict): Raw job data from Ashby API.
        company_name (str): The name of the company to associate with the jobs.
        Returns:
        List[Job]: A list of new Job instances not yet in the database.
    """
    jobs_data = json_data.get("jobs", [])
    jobs: List[Job] = []

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        # Skip job if company isn't found (or you can create a fallback company)
        return []

    candidate_urls = [job.get("jobUrl") for job in jobs_data if job.get("jobUrl")]
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    for job in jobs_data:
        job_url = job.get("jobUrl")

        if job_url and job_url not in existing_urls:
            published_date = job.get("publishedAt")
            job_date = datetime.fromisoformat(published_date).date()

            job_instance = Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job.get("id"),
                job_date=job_date,
                job_title=job.get("title"),
                active=True,
                location=job.get("location"),
                date_added=date.today()
            )
            jobs.append(job_instance)
    return jobs

def get_ashby_jobs(api_url: str, company_name: str) -> List[Job]:
    """
    Fetch and extract new jobs from the Ashby API.

    Args:
        api_url (str): The Ashby API URL for job listings.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        List[Job]: A list of new Job instances not yet in the database.
    """
    json_data = get_jobs(api_url)
    return extract_new_jobs(json_data, company_name)
