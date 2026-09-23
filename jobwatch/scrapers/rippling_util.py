from datetime import date

from typing import List, Dict
from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json

def get_jobs(api_url: str) -> Dict:
    return request_json("GET", api_url, timeout=10)

def extract_new_jobs(json_data: Dict, company_name: str) -> List[Job]:
    jobs_data = json_data.get("items", [])
    jobs: List[Job] = []
    seen_ids = set()

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        return []

    candidate_urls = [job.get("url") for job in jobs_data if job.get("url")]
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    for job in jobs_data:
        job_url = job.get("url")
        job_id = job.get("id")

        if not job_id or job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        # Skip if job already exists in DB by URL
        if job_url and job_url not in existing_urls:
            job_instance = Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job_id,
                job_date=date.today(),  # Rippling does not provide posted date
                job_title=job.get("name"),
                active=True,
                location=job.get("locations", [])[0].get("country") if job.get("locations") else "",
                date_added=date.today()
            )
            jobs.append(job_instance)
    return jobs

def get_rippling_jobs(api_url: str, company_name: str) -> List[Job]:
    """
    Fetch and extract new jobs from the Rippling API.

    Args:
        api_url (str): The Rippling API URL for job listings.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        List[Job]: A list of new Job instances not yet in the database.
    """
    raw_jobs = get_jobs(api_url)
    return extract_new_jobs(raw_jobs, company_name)
