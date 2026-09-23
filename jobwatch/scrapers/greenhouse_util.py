from datetime import datetime, date

from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json


def get_jobs(api_url: str) -> dict:
    """
    Fetch raw job data from the Greenhouse API for a specific board.

    Args:
        api_url (str): The Greenhouse API URL for job listings.

    Returns:
        dict: raw job data from the Greenhouse API.
    """
    return request_json("GET", api_url, timeout=10)


def extract_new_jobs(json_data: dict, company_name: str) -> list[Job]:
    """
    Extracts job objects from Greenhouse API JSON data, only if they are not already in the database.

    Args:
        json_data (dict): Raw job data from Greenhouse API.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        list[Job]: A list of new Job instances not yet in the database.
    """
    jobs_data = json_data.get("jobs", [])
    jobs: list[Job] = []

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        # Skip job if company isn't found (or you can create a fallback company)
        return []

    candidate_urls = [job.get("absolute_url") for job in jobs_data if job.get("absolute_url")]
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    for job in jobs_data:
        job_url = job.get("absolute_url")

        if job_url and job_url not in existing_urls:
            job_id = job.get("id")
            job_date = (
                datetime.fromisoformat(job.get("updated_at")).date()
                if job.get("updated_at")
                else date.today()
            )

            job_instance = Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job_id,
                job_date=job_date,
                job_title=job.get("title", ""),
                active=True,
                location=job.get("location", {}).get("name", "Unknown Location"),
                date_added=date.today()
            )
            jobs.append(job_instance)

    return jobs

def get_greenhouse_jobs(api_url: str, company_name: str) -> list[Job]:
    """
    Fetch and extract new jobs from the Greenhouse API.

    Args:
        api_url (str): The Greenhouse API URL for job listings.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        list[Job]: A list of new Job instances.
    """
    json_data = get_jobs(api_url)
    return extract_new_jobs(json_data, company_name)
