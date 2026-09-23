from types import SimpleNamespace

from jobwatch.helpers.job_sorter import categorize_jobs
from jobwatch.models.Job import JobCategoryType


def test_categorize_jobs_sets_matching_category_and_keeps_unmatched_category():
    backend_role = SimpleNamespace(job_title="Senior Backend Engineer", category=None)
    unmatched_role = SimpleNamespace(job_title="Chief Executive Officer", category=JobCategoryType.OTHER)
    jobs = [backend_role, unmatched_role]

    result = categorize_jobs(jobs)

    assert result is jobs
    assert backend_role.category is JobCategoryType.SOFTWARE
    assert unmatched_role.category is JobCategoryType.OTHER
