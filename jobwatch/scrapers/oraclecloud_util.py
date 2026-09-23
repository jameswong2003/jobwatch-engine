from datetime import date, datetime
from urllib.parse import urlparse

from typing import List, Dict, Tuple
from jobwatch.models.Job import Job
import jobwatch.db.job_queries as job_queries
import jobwatch.db.company_queries as company_queries
from jobwatch.scrapers.client import request_json

"""
Utility functions for interacting with the Oracle Cloud job postings API.
API URL is as follows:
GET: https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions

Params:
?
onlyData=true
&
expand=requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields
&
finder=findReqs;siteNumber=CX_1001,facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,limit=150,locationId=300000000289738,sortBy=POSTING_DATES_DESC
"""

def get_jobs(api_url: str) -> Tuple[Dict, str]:
    """
    Fetch jobs from the Oracle Cloud API.
    """
    parsed = urlparse(api_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return request_json("GET", api_url, timeout=10), base_url

def extract_new_jobs(json_data: Dict, company_name: str, base_url: str) -> List[Job]:
    jobs_data = json_data.get("items", [])[0].get("requisitionList", [])
    jobs: List[Job] = []

    company = company_queries.get_company_by_name(company_name)
    if company is None:
        # Skip job if company isn't found (or you can create a fallback company)
        return []

    candidate_urls = [
        f"{base_url}/hcmUI/CandidateExperience/en/sites/CX_1001/job/{job.get('Id')}"
        for job in jobs_data
    ]
    existing_urls = job_queries.get_existing_job_posting_urls(candidate_urls)

    for job in jobs_data:
        job_id = job.get("Id")
        job_url = f"{base_url}/hcmUI/CandidateExperience/en/sites/CX_1001/job/{job_id}"

        if job_url and job_url not in existing_urls:
            job_instance = Job(
                company_id=company.id,
                job_posting_url=job_url,
                job_id=job_id,
                job_date=datetime.strptime(job.get("PostedDate"), "%Y-%m-%d").date(),
                job_title=job.get("Title"),
                active=True,
                location=job.get("PrimaryLocation", ""),
                date_added=date.today()
            )
            jobs.append(job_instance)
    return jobs

def get_oracle_cloud_jobs(api_url: str, company_name: str) -> List[Job]:
    """
    Fetch and extract new jobs from the Oracle Cloud API.

    Args:
        api_url (str): The Oracle Cloud API URL for job listings.
        company_name (str): The name of the company to associate with the jobs.

    Returns:
        List[Job]: A list of new Job instances not yet in the database.
    """
    json_data, base_url = get_jobs(api_url)
    return extract_new_jobs(json_data, company_name, base_url)
