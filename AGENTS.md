# AGENTS.md

This file provides repository-wide guidance for coding agents working on JobWatch.
When this file and the implementation disagree, inspect the current code and treat
the code as the source of truth. Keep this guide updated when behavior changes.

## Project overview

JobWatch polls company job-board APIs, categorizes newly discovered postings,
stores them in SQLite, and emails a digest grouped by company. Scrape failures are
stored and included in the digest so one broken company board does not hide the
results from other boards.

The project is a small Python application using SQLAlchemy, blocking `requests`
scrapers, and an asynchronous polling loop. A small pytest suite runs in GitHub
Actions. There is currently no migration tool, linter, or build step configured.

## Common commands

```bash
source venv/bin/activate
pip install -r requirements.txt
python main.py
python main.py --category SOFTWARE
python main.py --dry-run
python main.py --company_id 42
python manage.py list
python manage.py import --file jobwatch/db/initial_data/companies.json
python -m jobwatch.db.init_db
```

Use `python3` instead of `python` when the environment does not provide a
`python` executable.

`--category` filters only the email digest. All discovered jobs are still
categorized and persisted. `--dry-run` skips writes for scraped jobs/errors and
skips email delivery; normal startup initialization still runs.
`--company_id` limits each polling cycle to the company with that database ID.
An unknown ID exits with an error before polling starts. Companies without an
enabled API continue to be skipped as in an unfiltered run.

Runtime configuration comes from `.env` via `python-dotenv`:

- `POLL_INTERVAL_SECONDS` is optional and defaults to `3600`.
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `EMAIL_TO` are required for
  normal runs.
- `SMTP_PORT` defaults to `587`; `EMAIL_FROM` defaults to `SMTP_USERNAME`.

## Repository layout

- `main.py`: thin runtime entrypoint and CLI parsing.
- `manage.py`: company-management CLI.
- `jobwatch/service/`: polling orchestration, configuration, and notifications.
- `jobwatch/scrapers/`: generic board scrapers and custom company scrapers.
- `jobwatch/helpers/`: board dispatch, categorization, URL cleanup, and constants.
- `jobwatch/db/`: engine/session setup, database queries, initialization, and seed
  data.
- `jobwatch/models/`: SQLAlchemy ORM models and enums.

Keep business and database logic in these modules rather than growing the
entrypoints.

## Runtime flow

`main.py` initializes the schema and initial company data, loads configuration,
and runs `jobwatch.service.job_processor.process_job_cycle` repeatedly, sleeping
for `POLL_INTERVAL_SECONDS` between cycles. The process continues after a cycle
failure; `KeyboardInterrupt` stops the loop.

Each polling cycle:

1. Iterates through the loaded `Company` rows.
2. Skips companies where `has_api` is false.
3. Dispatches to the correct scraper through `helpers.mapper.api_mapper`.
4. Converts each company-level failure into one `ErrorLog` without aborting the
   rest of the cycle.
5. Categorizes new jobs and inserts them in batches.
6. Inserts error logs from the cycle.
7. Sends one digest when there are new jobs, errors, or both.

The scrapers and SMTP client are blocking, so the async orchestration calls them
through `asyncio.to_thread`. Do not add blocking network or email work directly to
the event loop.

## Scraper contract

Generic board modules follow three layers:

1. A fetch function calls the remote API with a timeout and returns decoded JSON.
2. `extract_new_jobs(...)` looks up the company once, fetches existing job keys in
   one batched query, and maps only new postings to `Job` objects.
3. `get_<board>_jobs(...)` combines fetching and extraction and is called by
   `api_mapper`.

Important invariants:

- Never reintroduce a per-posting database lookup. Existing job URLs or IDs must
  be fetched for the whole response in one query.
- Pass `company_name` explicitly through every scraper. Do not depend on the API
  response containing a reliable company name.
- Network calls should use a finite timeout; existing scrapers use 10 seconds.
- A malformed or unsuccessful board response should raise a useful exception so
  the processor can record an `ErrorLog`.
- New generic board types need an enum value, scraper module, and `api_mapper`
  branch. Custom providers should follow the Amazon folder pattern under
  `jobwatch/scrapers/custom_scrapers/`.

Provider details:

- Greenhouse and Ashby use `GET` and return an object containing a `jobs` list.
- Lever uses `GET` and returns a bare list.
- Workday uses `POST`; build posting URLs from `Company.company_job_url` and the
  posting `externalPath`. Use the resulting posting URL as the job identity, like
  every other provider.
- Amazon is a custom scraper with a fixed request body and currently limited
  pagination/filter behavior; verify its intended scope before expanding it.
- Oracle, SmartRecruiters, and Rippling have provider-specific request shapes;
  inspect their modules before changing shared assumptions.

## Models and persistence

`Company` stores the public careers URL, board type, API-enabled flag, and API
URL. `Job` belongs to a company and is uniquely identified by its globally unique
posting URL. `job_id` is provider metadata and is not used for uniqueness.
`ErrorLog` belongs to a company and also stores snapshots of the company name and
URLs from the time of failure.

Use `job.company.company_name`; `Job` does not have a `company_name` field.

The SQLite database is `jobwatch/db/app.db`, resolved relative to the database
module rather than the process working directory. Database sessions belong in
`company_queries.py`, `job_queries.py`, or `error_log_queries.py`. Each query
function should open its own `SessionLocal`, commit or roll back as appropriate,
and close the session in `finally`.

SQLite foreign-key cascades are not relied upon here. Company removal explicitly
deletes dependent jobs and error logs.

## Managing company data

For a single company, prefer the `manage.py add`, `update`, and `remove` commands.
The initial startup seed is additive and matches by company name; it does not
update existing records.

For a shareable company list, use:

```bash
python manage.py import --file path/to/companies.json
```

The import format is a JSON list. Every record requires an explicit positive
integer `id`, `company_name`, `company_job_url`, `job_board_type`, and `has_api`.
An enabled API also requires `api_url`.

Import semantics are intentionally ID-based and non-destructive:

- Existing IDs are updated in place.
- Missing IDs are inserted with the supplied ID.
- Companies absent from the file remain in the database.
- Related jobs and error logs remain attached because rows are updated rather
  than deleted and reinserted.
- The complete list is validated before the transaction is committed.

Do not change this into name-based matching or delete-and-reinsert behavior.

## Categorization and notifications

`helpers.filter_constants.JOB_FILTERS` is keyed by `JobCategoryType` values, not
necessarily enum member names. Convert those values with `JobCategoryType(value)`
rather than `JobCategoryType[value]`.

The email client produces HTML and plain-text bodies. Preserve HTML escaping for
all company, job, and error text because it originates from external systems.
Errors must still be sent when a cycle discovers no new jobs.

## Validation expectations

For changes:

- Run `python3 -m py_compile` on touched Python modules.
- Use focused, isolated checks for the behavior being changed.
- Use a temporary SQLite database for database tests; do not mutate the user's
  `jobwatch/db/app.db` during verification.
- Do not call live job-board APIs or send email unless the task explicitly needs
  an integration check and the user has supplied the necessary authorization and
  configuration.
- Run `git diff --check` and inspect the final diff before handing off.

Preserve unrelated working-tree changes and keep refactors separate from the
requested behavior.
