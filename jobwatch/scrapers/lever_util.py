from datetime import datetime, date, timezone
from typing import List, Dict

from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json

# Example Lever.co API Call
# GET https://api.lever.co/v0/postings/{company_name}

def get_jobs(api_url: str) -> List[Dict]: # Lever.co returns a list, rather than a dict
    """
    Fetch jobs from the Lever.co API.
    """
    return request_json("GET", api_url, timeout=10)

def extract_new_jobs(json_data: List[Dict], company_name: str) -> List[Job]:
    """
    Extracts job objects from lever.co API JSON data, only if they are not already in the database.

    Args:
        json_data (dict): Raw job data from lever.co API.
        company_name (str): Optional override for company name if not included in job data.

    Returns:
        list[Job]: A list of new Job instances not yet in the database.
    """
    jobs: List[Job] = []

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        return []

    candidate_urls = [job.get("hostedUrl") for job in json_data if job.get("hostedUrl")]
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    for job in json_data:
        job_url = job.get("hostedUrl")

        if job_url and job_url not in existing_urls:
            job_date = datetime.fromtimestamp(job.get("createdAt") / 1000, tz=timezone.utc)

            job_instance = Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job.get("id"),
                job_date=job_date,
                job_title=job.get("text"),
                active=True,
                location=job.get("categories").get("location"),
                date_added=date.today()
            )
            jobs.append(job_instance)
    return jobs

def get_lever_jobs(api_url: str, company_name: str) -> List[Job]:
    """
    Fetch and extract new jobs from Lever.co API for a specific company.

    Args:
        api_url (str): The Lever.co API URL for job listings.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        List[Job]: A list of new Job instances not yet in the database.
    """
    raw_jobs = get_jobs(api_url)
    return extract_new_jobs(raw_jobs, company_name)
