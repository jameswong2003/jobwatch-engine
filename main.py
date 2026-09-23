import argparse
import asyncio

from dotenv import load_dotenv

from jobwatch.db.company_queries import get_company_by_id
from jobwatch.db.init_db import init_db, insert_initial_companies
from jobwatch.models.Job import JobCategoryType
from jobwatch.service.config import load_email_config, load_poll_interval_seconds
from jobwatch.service.job_processor import job_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JobWatch - poll job boards and notify on new postings")
    parser.add_argument(
        "--category",
        type=str,
        choices=[category.name for category in JobCategoryType],
        default=None,
        help="Only include jobs of this category in the email digest (all jobs are still scraped and stored)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and print what would be emailed, without writing to the DB or sending an email (does not require SMTP env vars)",
    )
    parser.add_argument(
        "--company_id",
        type=int,
        default=None,
        help="Only scrape the company with this database ID",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    category_filter = JobCategoryType[args.category] if args.category else None

    load_dotenv()
    init_db()
    insert_initial_companies()

    if args.company_id is not None and get_company_by_id(args.company_id) is None:
        print(f"Error: no company found with ID {args.company_id}")
        raise SystemExit(1)

    poll_interval_seconds = load_poll_interval_seconds()
    email_config = None if args.dry_run else load_email_config()

    await job_loop(
        poll_interval_seconds,
        email_config,
        category_filter,
        dry_run=args.dry_run,
        company_id=args.company_id,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
