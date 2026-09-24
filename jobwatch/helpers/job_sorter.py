from typing import List, Tuple
from jobwatch.models.job_types import JobCategoryType
from jobwatch.helpers.filter_constants import JOB_FILTERS

def categorize_jobs(jobs: List) -> List:
    for job in jobs:
        job_title: str = job.job_title.lower()
        for category, keywords in JOB_FILTERS.items():
            if any(keyword in job_title for keyword in keywords):
                job.category = JobCategoryType(category)
                break
    
    return jobs