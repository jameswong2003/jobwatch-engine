# JobWatch Engine

JobWatch polls a collection of company job-board APIs on a configurable interval, categorizes new job postings by keyword, stores them in a local SQLite database, and sends an email digest grouped by company. The digest includes any scrape errors from the cycle, ensuring visibility when a company's job board breaks or they switch ATS providers.

## Features

- **Multi-board support**: Scrapes jobs from Ashby, Greenhouse, Workday, Lever, Oracle, SmartRecruiters, Rippling, and Amazon (via custom scraper)
- **Keyword-based categorization**: Automatically assigns jobs to categories (e.g. Software, Hardware, Finance, Data Science, Product, Design/UX, Marketing, Sales, Operations, HR, Legal, Customer Support, Engineering, Medical, Education)
- **Email digest**: Sends formatted emails with job postings grouped by company (company names in bold, job titles in italics), plus an error section if any scrapes failed
- **Category filtering**: Use `--category` to restrict the email digest to a single job category without affecting what gets scraped or stored
- **Error logging**: Captures and stores scrape failures with timestamps and original board URLs, helping identify when companies have switched job-board providers
- **No external dependencies for data**: All jobs stored in local SQLite; no cloud storage or external APIs required for persistence

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

3. Set up your environment file. Copy `.env.example` to `.env` and fill in your SMTP credentials:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with:
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` — your email provider's SMTP settings
   - `EMAIL_FROM`, `EMAIL_TO` — sender and recipient email addresses
   - `POLL_INTERVAL_SECONDS` — seconds between scrape cycles (defaults to 3600 / 1 hour)

   **Note for Gmail users**: Generate an [App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification enabled) and use that in `SMTP_PASSWORD` instead of your account password.

   The database and initial companies are set up automatically when you run `main.py` for the first time.

## Usage

### Run a scrape cycle
```bash
python main.py
```

This fetches jobs from all configured company boards, categorizes them, stores new postings in the database, and sends an email digest.

### Filter the email digest by category
```bash
python main.py --category SOFTWARE
```

Only jobs in the specified category appear in the email; all jobs are still scraped and stored. Valid categories include:
- `SOFTWARE`, `HARDWARE`, `FINANCE`, `DATA_SCIENCE`, `PRODUCT`, `DESIGN`, `MARKETING`, `SALES`, `OPERATIONS`, `HUMAN_RESOURCES`, `LEGAL`, `CUSTOMER_SUPPORT`, `ENGINEERING`, `MEDICAL`, `EDUCATION`, `OTHER`

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

Jobs are persisted in `jobwatch/db/app.db` (SQLite, resolved relative to the `database.py` module — works correctly regardless of your working directory). The schema includes:

- **Company**: Stores board type, job board URL, and API endpoint for each company
- **Job**: Job title, posting URL, date posted, date added, category, and link to company
- **ErrorLog**: Scrape failures with company name, original URLs, and error message snapshots for manual triage

## Architecture Notes

- All scraping is asynchronous via `asyncio` with blocking I/O run in thread pools
- Email sending also runs in a thread pool (SMTP is blocking)
- Each scrape cycle is independent; a failure on one company's board doesn't affect others
- Jobs are deduplicated by posting URL (globally unique) across all boards, including Workday

## Testing & Linting

Install the development dependencies and run the test suite:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

GitHub Actions runs the test suite on pushes and pull requests. See
[CONTRIBUTING.md](CONTRIBUTING.md) for safe validation guidance. Routine checks
do not call live job-board APIs or send email.

### Existing SQLite databases

The local `jobwatch/db/app.db` file must be removed by the user when applying the
current schema change; normal startup recreates it. This removes existing local
jobs and companies, so export any data you want to keep first. The application does
not delete the database automatically.

## License

[MIT](LICENSE)
