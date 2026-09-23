# Contributing

Thanks for helping improve JobWatch. Before making a change, check the existing
scraper and database conventions in [AGENTS.md](AGENTS.md), then keep changes
focused on the behavior you are adding or fixing.

## Local setup

Install the project dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

Running `main.py` performs network requests to configured job boards and can
send email. Do not use it as a routine validation command. You do not need a
real `.env`, job-board account, or SMTP provider to contribute or validate code.

## Scraper conventions

Generic board integrations belong in `jobwatch/scrapers/`; provider-specific
integrations can live under `jobwatch/scrapers/custom_scrapers/`. Follow the
existing module pattern:

1. Fetch JSON using a finite request timeout and raise a useful exception for
   unsuccessful or malformed responses.
2. Extract new postings with the company name passed explicitly. Look up the
   company once and fetch existing posting keys in one batched database query;
   do not add a database lookup for each posting.
3. Expose a `get_<board>_jobs(...)` function and register the board in
   `jobwatch/helpers/mapper.py` and `JobBoardType` when adding a generic board.

Preserve the provider's response shape and URL rules. In particular, inspect
the existing Workday, Oracle, SmartRecruiters, Rippling, and Amazon modules
before changing shared scraper assumptions.

## Safe validation

Run the automated tests before submitting a change:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

GitHub Actions runs these tests for pushes and pull requests. For Python
changes, syntax compilation can also help catch import-time syntax errors in
touched modules, for example:

```bash
python3 -m py_compile jobwatch/scrapers/example_util.py
```

Use focused checks with mocked HTTP responses and a temporary SQLite database
when behavior needs validation. Do not call live job-board APIs, send email, or
use `jobwatch/db/app.db` for database checks. If a change requires an integration
check, make that explicit in the contribution description and document exactly
what was exercised.

Before submitting, inspect the diff and run:

```bash
git diff --check
```

## Pull requests

Describe the behavior changed, the validation performed, and any limitations.
Keep unrelated formatting or refactoring out of the change so it is easier to
review.
