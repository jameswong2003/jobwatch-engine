import argparse
import json
from pathlib import Path

from jobwatch.db.company_queries import (
    delete_company_by_name,
    get_all_companies,
    get_company_by_name,
    insert_company,
    upsert_companies,
    update_company,
)
from jobwatch.db.init_db import init_db
from jobwatch.models.Company import JobBoardType


DEFAULT_COMPANIES_FILE = Path(__file__).resolve().parent / "jobwatch" / "db" / "initial_data" / "companies.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage JobWatch companies")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List all companies")
    list_parser.add_argument(
        "--board-type",
        type=str,
        choices=[board.name for board in JobBoardType],
        default=None,
        help="Only list companies with this job board type",
    )

    add_parser = subparsers.add_parser("add", help="Add a new company")
    add_parser.add_argument("--name", required=True, help="Company name")
    add_parser.add_argument("--job-url", required=True, help="Public careers page URL")
    add_parser.add_argument(
        "--board-type",
        type=str,
        required=True,
        choices=[board.name for board in JobBoardType],
        help="Job board type",
    )
    add_parser.add_argument("--api-url", default=None, help="Job board API URL (required unless --no-api)")
    add_parser.add_argument(
        "--no-api",
        action="store_true",
        help="Mark this company as having no scrapable API (skips scraping)",
    )

    remove_parser = subparsers.add_parser("remove", help="Remove a company and its jobs/errors")
    remove_parser.add_argument("--name", required=True, help="Company name to remove")

    update_parser = subparsers.add_parser("update", help="Update an existing company")
    update_parser.add_argument("--name", required=True, help="Current company name")
    update_parser.add_argument("--new-name", default=None, help="Rename the company")
    update_parser.add_argument("--job-url", default=None, help="New public careers page URL")
    update_parser.add_argument("--api-url", default=None, help="New job board API URL")
    update_parser.add_argument(
        "--board-type", type=str, default=None, choices=[b.name for b in JobBoardType],
        help="New job board type",
    )
    update_parser.add_argument("--enable-api", action="store_true", help="Mark company as having a scrapable API")
    update_parser.add_argument("--disable-api", action="store_true", help="Mark company as having no scrapable API")

    import_parser = subparsers.add_parser("import", help="Import companies from a JSON file by ID")
    import_parser.add_argument(
        "--file",
        default=str(DEFAULT_COMPANIES_FILE),
        help=f"JSON file containing companies (default: {DEFAULT_COMPANIES_FILE})",
    )

    return parser.parse_args()


def list_companies(board_type: str | None) -> None:
    companies = get_all_companies()
    if board_type:
        companies = [c for c in companies if c.job_board_type.name == board_type]

    if not companies:
        print("No companies found.")
        return

    print(f"{'ID':<5} {'Name':<30} {'Board Type':<16} {'Has API':<8} API URL")
    for company in companies:
        print(
            f"{company.id:<5} {company.company_name:<30} {company.job_board_type.name:<16} "
            f"{str(company.has_api):<8} {company.api_url or '-'}"
        )


def add_company(name: str, job_url: str, board_type: str, api_url: str | None, no_api: bool) -> None:
    has_api = not no_api
    if has_api and not api_url:
        print("Error: --api-url is required unless --no-api is passed.")
        return

    if get_company_by_name(name) is not None:
        print(f"Error: a company named '{name}' already exists.")
        return

    company_id = insert_company(
        company_name=name,
        company_job_url=job_url,
        job_board_type=JobBoardType[board_type],
        has_api=has_api,
        api_url=None if no_api else api_url,
    )
    print(f"Added company '{name}' with id {company_id}.")


def remove_company(name: str) -> None:
    result = delete_company_by_name(name)
    if result is None:
        print(f"Error: no company named '{name}' found.")
        return

    print(
        f"Removed '{name}' along with {result['jobs_deleted']} job(s) "
        f"and {result['errors_deleted']} error log entr(y/ies)."
    )


def update_company_handler(
    name: str,
    new_name: str | None,
    job_url: str | None,
    api_url: str | None,
    board_type: str | None,
    enable_api: bool,
    disable_api: bool,
) -> None:
    if enable_api and disable_api:
        print("Error: cannot pass both --enable-api and --disable-api.")
        return

    has_api = None
    if enable_api:
        has_api = True
    elif disable_api:
        has_api = False

    job_board_type = None
    if board_type is not None:
        job_board_type = JobBoardType[board_type]

    result = update_company(
        name=name,
        new_name=new_name,
        company_job_url=job_url,
        job_board_type=job_board_type,
        has_api=has_api,
        api_url=api_url,
    )
    if result is None:
        print(f"Error: no company named '{name}' found.")
        return

    print(f"Updated company '{name}'.")


def _load_companies_file(filepath: str) -> list[dict]:
    try:
        with open(filepath, encoding="utf-8") as file:
            companies = json.load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {filepath}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {filepath}: {exc.msg} (line {exc.lineno}, column {exc.colno})") from exc

    if not isinstance(companies, list):
        raise ValueError("the JSON root must be a list of company objects")

    normalized = []
    seen_ids = set()
    required_fields = {"id", "company_name", "company_job_url", "job_board_type", "has_api"}

    for index, company in enumerate(companies, start=1):
        if not isinstance(company, dict):
            raise ValueError(f"record {index} must be a JSON object")

        missing_fields = required_fields - company.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"record {index} is missing required field(s): {missing}")

        company_id = company["id"]
        if isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0:
            raise ValueError(f"record {index} has invalid id; expected a positive integer")
        if company_id in seen_ids:
            raise ValueError(f"record {index} has duplicate id: {company_id}")
        seen_ids.add(company_id)

        for field in ("company_name", "company_job_url"):
            if not isinstance(company[field], str) or not company[field].strip():
                raise ValueError(f"record {index} field '{field}' must be a non-empty string")

        board_type = company["job_board_type"]
        if not isinstance(board_type, str) or board_type not in JobBoardType.__members__:
            valid_types = ", ".join(JobBoardType.__members__)
            raise ValueError(f"record {index} has invalid job_board_type '{board_type}'; expected one of: {valid_types}")

        has_api = company["has_api"]
        if not isinstance(has_api, bool):
            raise ValueError(f"record {index} field 'has_api' must be a boolean")

        api_url = company.get("api_url")
        if api_url is not None and (not isinstance(api_url, str) or not api_url.strip()):
            raise ValueError(f"record {index} field 'api_url' must be a non-empty string or null")
        if has_api and not api_url:
            raise ValueError(f"record {index} must include 'api_url' when has_api is true")

        normalized.append(
            {
                "id": company_id,
                "company_name": company["company_name"],
                "company_job_url": company["company_job_url"],
                "job_board_type": JobBoardType[board_type],
                "has_api": has_api,
                "api_url": api_url,
            }
        )

    return normalized


def import_companies(filepath: str) -> bool:
    try:
        companies = _load_companies_file(filepath)
        init_db()
        counts = upsert_companies(companies)
    except (OSError, ValueError) as exc:
        print(f"Error importing companies: {exc}")
        return False
    except Exception as exc:
        print(f"Error importing companies; no changes were committed: {exc}")
        return False

    print(
        f"Imported {len(companies)} compan{'y' if len(companies) == 1 else 'ies'}: "
        f"{counts['inserted']} added, {counts['updated']} updated, {counts['unchanged']} unchanged."
    )
    return True


def main() -> None:
    args = parse_args()

    if args.command == "list":
        list_companies(args.board_type)
    elif args.command == "add":
        add_company(args.name, args.job_url, args.board_type, args.api_url, args.no_api)
    elif args.command == "remove":
        remove_company(args.name)
    elif args.command == "update":
        update_company_handler(
            args.name,
            args.new_name,
            args.job_url,
            args.api_url,
            args.board_type,
            args.enable_api,
            args.disable_api,
        )
    elif args.command == "import":
        if not import_companies(args.file):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
