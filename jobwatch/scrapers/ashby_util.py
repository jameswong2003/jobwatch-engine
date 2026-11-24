from datetime import date

from jobwatch.scrapers.job_candidate import JobCandidate
from jobwatch.scrapers.client import request_json

API_URL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
QUERY = """
query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
  jobBoard: jobBoardWithTeams(
    organizationHostedJobsPageName: $organizationHostedJobsPageName
  ) {
    jobPostings {
      id
      title
      locationName
    }
  }
}
"""


def get_jobs(hosted_jobs_page_name: str) -> dict:
    return request_json("POST", API_URL, json={
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": hosted_jobs_page_name},
        "query": QUERY,
    }, timeout=10)


def extract_jobs(json_data: dict, company_id: int, hosted_jobs_page_name: str) -> list[JobCandidate]:
    if json_data.get("errors"):
        raise ValueError(f"Ashby GraphQL errors: {json_data['errors']}")
    data = json_data.get("data")
    job_board = data.get("jobBoard") if isinstance(data, dict) else None
    jobs_data = job_board.get("jobPostings") if isinstance(job_board, dict) else None
    if not isinstance(jobs_data, list):
        raise ValueError("Ashby response is missing data.jobBoard.jobPostings")
    jobs: list[JobCandidate] = []
    for job in jobs_data:
        job_id = job.get("id")
        if not job_id:
            continue
        jobs.append(JobCandidate(
            company_id=company_id,
            job_posting_url=f"https://jobs.ashbyhq.com/{hosted_jobs_page_name}/{job_id}",
            job_id=str(job_id), job_date=date.today(), job_title=job.get("title") or "",
            active=True, location=job.get("locationName"), date_added=date.today(),
        ))
    return jobs


def get_ashby_jobs(company, api_config: dict) -> list[JobCandidate]:
    hosted_jobs_page_name = api_config.get("organizationHostedJobsPageName")
    if not isinstance(hosted_jobs_page_name, str) or not hosted_jobs_page_name.strip():
        raise ValueError("Ashby api_config.organizationHostedJobsPageName must be a non-empty string")
    return extract_jobs(get_jobs(hosted_jobs_page_name), company.company_id, hosted_jobs_page_name)
