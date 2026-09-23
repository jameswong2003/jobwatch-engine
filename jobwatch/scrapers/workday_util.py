'''
Workday API utility functions

Url can be found in network tab

EXAMPLE URL:
POST
https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs
https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs

RAW BODY:
{"appliedFacets":{},"limit":20,"offset":2,"searchText":""}
'''
from datetime import date

from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json

def get_jobs(url: str, limit: int = 20, offset: int = 0, searchText: str = "") -> dict:
    """
    Fetch raw job data from a Workday API endpoint.

    Args:
        url (str): Full Workday job postings API endpoint.
        limit (int): Number of job results to retrieve.
        offset (int): Offset for pagination.
        searchText (str): Optional search text to filter jobs.

    Returns:
        dict: Raw JSON response from the Workday API.
    """
    json_body = {
        "appliedFacets": {},
        "limit": limit,
        "offset": offset,
        "searchText": searchText
    }

    return request_json("POST", url, json=json_body, timeout=10)


def extract_new_jobs(json_data: dict, company_name: str = "") -> list[Job]:
    """
    Convert a list of Workday job postings to Job model instances.

    Args:
        json_data (dict): Raw response from the Workday API.
        company_name (str): Optional company name.
        base_url (str): Optional base URL used to populate job URLs if needed.

    Returns:
        list[Job]: List of Job instances.
    """
    job_postings = json_data.get("jobPostings", [])
    job_list = []

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        return []

    candidate_ids = [posting.get("externalPath", "") for posting in job_postings]
    existing_ids = job_queries.get_existing_job_ids_for_company(company.id, candidate_ids)

    for posting in job_postings:
        # externalPath (the posting's own URL path) uniquely identifies a posting within
        # a company. bulletFields is a set of UI display badges (e.g. "Spotlight Job")
        # that Workday can reuse across multiple postings, so it isn't a valid job ID.
        internal_job_id = posting.get("externalPath", "")

        if internal_job_id in existing_ids:
            continue  # Skip if job already exists

        full_job_url = f"{company.company_job_url}{posting.get('externalPath', '')}"

        job_list.append(Job(
            company_id=company.id,
            job_posting_url=full_job_url,
            job_id=internal_job_id,
            job_date=date.today(),
            job_title=posting.get("title", ""),
            active=True,  # Assuming all fetched jobs are active
            location=posting.get("locationsText"),
            date_added=date.today()
        ))

    return job_list

def get_workday_jobs(api_url: str, company_name: str) -> list[Job]:
    """
    Fetch and extract new jobs from the Workday API.

    Args:
        api_url (str): The Workday API URL for job listings.
        company_name (str): The name of the company to associate with the jobs. Lowercase is preferred.

    Returns:
        list[Job]: A list of new Job instances.
    """
    json_data = get_jobs(api_url)
    return extract_new_jobs(json_data, company_name)
