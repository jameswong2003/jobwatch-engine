# JobWatch Engine

## Using the scraper as a Python package

The database-independent scraping API is the package's core and has no database
or email dependency. From the engine checkout, install it with:

```bash
python -m pip install .
```

The engine's legacy standalone CLI and database modules are included as an
optional extra. Install the extra to run `main.py`, `manage.py`, or use the
inactive legacy email formatting helper:

```bash
python -m pip install '.[legacy]'
```

For backend development against a local checkout, use an editable install:

```bash
python -m pip install -e ../jobwatch-engine
```

The public scraping API accepts plain `CompanyConfig` values and returns every
posting reported by each enabled provider, including postings the caller may
already have stored. The caller is responsible for comparing and persisting
results:

```python
import asyncio

from jobwatch import CompanyConfig, JobBoardType, process_jobs_from_companies


async def main():
    companies = [
        CompanyConfig(
            company_id=1,
            company_name="Example",
            company_job_url="https://example.com/careers",
            job_board_type=JobBoardType.GREENHOUSE,
            has_api=True,
            api_url="https://boards-api.greenhouse.io/v1/boards/example/jobs",
        )
    ]
    jobs, errors = await process_jobs_from_companies(companies)
    print(f"Fetched {len(jobs)} jobs and {len(errors)} company errors")


asyncio.run(main())
```

The returned job values are `JobCandidate` instances. Each error is a
`ScrapeError` with company ID/name, source URLs, error message, and occurrence
time. Companies with `has_api=False` or no `api_url` are skipped. A string board
type may be supplied as either its enum value (for example, `"Greenhouse"`) or
enum name (for example, `"GREENHOUSE"`).

Importing the top-level `jobwatch` package for scraping does not initialize or
connect to the legacy database. The standalone `main.py` app uses the database
for its legacy polling and persistence flow; notifications belong to the
backend.

JobWatch polls a collection of company job-board APIs on a configurable interval, categorizes new job postings by keyword, and stores them in PostgreSQL. Scrape failures are stored for later review.

## Features

- **Multi-board support**: Scrapes jobs from Ashby, Greenhouse, Workday, Lever, Oracle, SmartRecruiters, Rippling, and Amazon (via custom scraper)
- **Keyword-based categorization**: Automatically assigns jobs to categories (e.g. Software, Hardware, Finance, Data Science, Product, Design/UX, Marketing, Sales, Operations, HR, Legal, Customer Support, Engineering, Medical, Education)
- **Error logging**: Captures and stores scrape failures with timestamps and original board URLs, helping identify when companies have switched job-board providers
- **PostgreSQL persistence**: Store jobs and scrape errors in a local or remote PostgreSQL database

## Setup

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jameswong2003/jobwatch-engine.git
   cd jobwatch-engine
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment file. Copy `.env.example` to `.env` and configure PostgreSQL:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with:
   - `DATABASE_URL` — required SQLAlchemy PostgreSQL URL. For a local server, use
     `postgresql+psycopg://jobwatch:password@localhost:5432/jobwatch`. For a
     remote server, use its host and credentials; append `?sslmode=require` if
     the provider requires SSL. Create the PostgreSQL server and database before
     starting JobWatch. Never commit real credentials.
   - `POLL_INTERVAL_SECONDS` — seconds between scrape cycles (defaults to 3600 / 1 hour)
   - `MAX_CONCURRENT_COMPANY_SCRAPES` — maximum company boards scraped at once
     (defaults to 10; use a lower value such as `2` on a low-memory server)

   JobWatch creates its tables and inserts initial companies automatically when
   you run `main.py` for the first time. It does not create the PostgreSQL server
   or database itself.

## Usage

### Run a scrape cycle
```bash
python main.py
```

This starts the standalone polling process. It fetches jobs from all configured company boards, categorizes them, stores new postings and scrape errors in the database, then repeats after `POLL_INTERVAL_SECONDS` (default: 86400 seconds). A failed cycle is logged and the process continues with the next cycle. Notifications are handled by the backend.

## Managing Companies

### Adding or updating a company

Use `manage.py` to add a new company or update an existing one:

**Add a new company:**
```bash
python manage.py add --name "Example Corp" --job-url "https://jobs.example.com/careers" \
  --board-type GREENHOUSE --api-url "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true"
```

**Update an existing company** (e.g., after a board API URL changes):
```bash
python manage.py update --name "Example Corp" --api-url "https://new-api-url.example.com"
```

Update supports partial changes — only the flags you pass are updated:
- `--new-name` — rename the company
- `--job-url` — update the public careers page URL
- `--api-url` — update the API endpoint
- `--board-type` — change the job board type
- `--enable-api` / `--disable-api` — mark whether the company has a scrapable API

**List all companies:**
```bash
python manage.py list
```

**Remove a company and all its jobs/error logs:**
```bash
python manage.py remove --name "Example Corp"
```

**Import or update companies from a JSON file:**
```bash
python manage.py import --file jobwatch/db/initial_data/companies.json
```

The file must contain a list of company records with explicit, unique numeric
`id` values. Existing rows are updated by `id`, new rows are inserted, and
companies missing from the file are left unchanged. Related jobs and error logs
are preserved. The `--file` argument defaults to the repository's
`jobwatch/db/initial_data/companies.json` file.

### For new job-board types

New job-board providers require a scraper module. See [CONTRIBUTING.md](CONTRIBUTING.md) for scraper conventions, the expected interface, and how to wire a provider into `jobwatch/helpers/mapper.py`.

### Initial seeding

On a fresh install, `main.py` automatically creates the database and seeds companies from `jobwatch/db/initial_data/companies.json`. Startup seeding is additive and does not update existing company records. To add or update a company, use `manage.py` commands rather than editing the JSON file. To apply seed-file updates to an existing database, use `python manage.py import --file jobwatch/db/initial_data/companies.json`.

## Database

Jobs are persisted in the PostgreSQL database selected by `DATABASE_URL`. The
same setting is loaded from `.env` for `main.py`, `manage.py`, and direct database
module use. The schema is created from the SQLAlchemy models when the app starts;
there is no migration system. The schema includes:

- **Company**: Stores board type, job board URL, and API endpoint for each company
- **Job**: Job title, posting URL, date posted, date added, category, and link to company
- **ErrorLog**: Scrape failures with company name, original URLs, and error message snapshots for manual triage

## Architecture Notes

- All scraping is asynchronous via `asyncio` with blocking I/O run in thread pools
- Each scrape cycle is independent; a failure on one company's board doesn't affect others
- Jobs are deduplicated by posting URL (globally unique) across all boards, including Workday

## Testing & Linting

Install the development dependencies and run the test suite:

```bash
python3 -m pip install -r requirements-dev.txt
DATABASE_URL=sqlite:///:memory: python3 -m pytest
```

GitHub Actions runs the test suite on pushes and pull requests. See
[CONTRIBUTING.md](CONTRIBUTING.md) for safe validation guidance. Routine checks
do not call live job-board APIs.

## License

[MIT](LICENSE)
