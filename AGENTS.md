# AGENTS.md

Guidance for coding agents working in `jobwatch-engine`. The implementation is
the source of truth; update this guide when architecture or commands change.

## Project shape

The engine is a Python package for scraping and normalizing company job-board
postings. Its public API is database-independent. A legacy standalone polling
CLI and SQLAlchemy persistence layer are also included for compatibility; the
backend owns notification delivery.

The public API exports `CompanyConfig`, `JobBoardType`, `JobCandidate`,
`ScrapeError`, and `process_jobs_from_companies` from `jobwatch/__init__.py`.
`process_jobs_from_companies` skips companies without an API URL, runs blocking
HTTP calls in worker threads with bounded concurrency, and returns every
normalized candidate plus per-company scrape errors. It does not query a
database or remove already-known postings. Callers own deduplication and
persistence.

The legacy `main.py` flow initializes the schema and inserts initial company
data, then repeatedly calls `jobwatch.service.job_processor.process_job_cycle`.
That adapter queries companies, scrapes through the public API, filters new
postings by posting URL in a batched query, and writes jobs and scrape errors.
`manage.py` provides the legacy company-management commands.

## Repository layout

- `jobwatch/__init__.py`: public, database-independent package API.
- `jobwatch/service/scraping.py`: async orchestration, concurrency limit, and
  `ScrapeError` creation.
- `jobwatch/scrapers/`: HTTP client, provider parsers, and `JobCandidate`.
  Provider-specific integrations may live under `custom_scrapers/`.
- `jobwatch/helpers/mapper.py`: board dispatch and categorization.
- `jobwatch/models/job_types.py`: board and job-category enums shared by the
  public API.
- `jobwatch/service/config.py`: polling and concurrency environment settings.
- `jobwatch/db/` and `jobwatch/models/Company.py`, `Job.py`, `ErrorLog.py`:
  optional legacy SQLAlchemy persistence.
- `main.py`, `manage.py`: legacy polling and company-management entrypoints.
- `tests/`: pytest coverage; CI runs it on Python 3.11 with an in-memory SQLite
  `DATABASE_URL`.

Keep package scraping behavior independent of the legacy database layer. The
standalone database imports require `DATABASE_URL`; importing the top-level
`jobwatch` package for scraping does not.

## Setup and common commands

The package requires Python 3.10 or newer. Install the package from this
directory with:

```bash
python3 -m pip install .
```

Install the optional legacy database dependencies to use `main.py`,
`manage.py`, or legacy database modules:

```bash
python3 -m pip install '.[legacy]'
```

For backend work against a local checkout, install it editable from the backend
directory with `python3 -m pip install -e ../jobwatch-engine`.

Useful legacy commands (run from the engine directory):

```bash
python3 main.py
python3 main.py --dry-run
python3 main.py --company_id 42
python3 manage.py list
python3 manage.py import --file jobwatch/db/initial_data/companies.json
```

`--dry-run` avoids job and scrape-error writes for the polling cycle, but startup
still initializes the schema and inserts missing seed companies. The company ID
option limits a cycle to one database row. The CLI needs a running database and
an existing database selected by `DATABASE_URL`.

The legacy CLI loads `.env` through `python-dotenv`. `DATABASE_URL` must be set
to a SQLAlchemy PostgreSQL URL for normal standalone use, for example
`postgresql+psycopg://user:password@localhost:5432/jobwatch`. The schema is
created with SQLAlchemy `create_all`; there is no migration tool. Polling
defaults to 86400 seconds (`POLL_INTERVAL_SECONDS`), and the scraper concurrency
defaults to 10 (`MAX_CONCURRENT_COMPANY_SCRAPES`). Concurrency must be a
positive integer.

## Scraper conventions and invariants

- Return database-independent `JobCandidate` values from provider integrations;
  pass company ID and company name explicitly.
- Keep blocking HTTP work out of the event loop. Use the shared request client
  and finite timeouts; current provider calls use 10 seconds.
- Preserve each provider's response format and URL rules. Inspect its scraper
  module before changing shared parsing assumptions.
- Raise useful exceptions for unsuccessful or malformed responses. The public
  orchestrator turns company-level exceptions into `ScrapeError` values and
  continues scraping other companies.
- When adding a generic board, update `JobBoardType`, add its scraper, and
  register it in `jobwatch/helpers/mapper.py`. Follow the existing custom
  scraper structure for provider-specific integrations.
- Scrapers do not access persistence or filter jobs by newness. In the legacy
  adapter, `job_posting_url` is the unique identity across providers; `job_id`
  is provider metadata.
- `Job` has no `company_name` field. Use the related `job.company.company_name`
  where a persisted company name is needed.
- The SQLAlchemy layer is optional. Keep public scraping imports free of
  database initialization and connection requirements.

## Coding principles

- Follow YAGNI: implement only what the current requirement needs.
- Prefer one-liner solutions when they remain clear and maintainable; do not
  compress complex logic just to reduce line count.
- Keep changes focused and preserve unrelated working-tree edits.

## Validation

Install the test dependencies and run the suite from the engine directory:

```bash
python3 -m pip install -r requirements-dev.txt
DATABASE_URL=sqlite:///:memory: python3 -m pytest
```

For Python changes, `python3 -m py_compile path/to/module.py` can check touched
modules. Use mocked HTTP responses for scraper checks and an isolated database
for persistence checks. Do not run `main.py` as a routine check: it calls live
job-board APIs and its startup can write schema and seed data. Do not send email
or use a configured user database during verification.

Before handing off, inspect the diff and run `git diff --check` from this
repository. Keep refactors and unrelated formatting changes out of the patch.
