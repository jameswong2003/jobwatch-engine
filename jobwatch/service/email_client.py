import smtplib
from email.message import EmailMessage
from html import escape
from typing import List, Tuple

from jobwatch.models.Job import Job
from jobwatch.models.ErrorLog import ErrorLog
from jobwatch.service.config import EmailConfig


def _group_by_company(jobs: List[Job]) -> dict[str, List[Job]]:
    grouped: dict[str, List[Job]] = {}
    for job in jobs:
        grouped.setdefault(job.company.company_name, []).append(job)
    return grouped


def _format_digest_text(jobs: List[Job]) -> str:
    """Plain-text fallback for clients that don't render HTML, e.g.:

    COMPANY NAME 1
    Job title --- job link
    """
    sections = []
    for company_name, company_jobs in _group_by_company(jobs).items():
        lines = [company_name]
        lines.extend(f"{job.job_title} --- {job.job_posting_url}" for job in company_jobs)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _format_digest_html(jobs: List[Job]) -> str:
    """HTML digest with bold company names and italic job titles, e.g.:

    <b>Company Name 1</b>
    <i>Job title</i> --- job link
    """
    sections = []
    for company_name, company_jobs in _group_by_company(jobs).items():
        job_lines = [
            f'<p><i>{escape(job.job_title)}</i> --- '
            f'<a href="{escape(job.job_posting_url)}">{escape(job.job_posting_url)}</a></p>'
            for job in company_jobs
        ]
        sections.append(f"<p><b>{escape(company_name)}</b></p>" + "".join(job_lines))

    return "".join(sections)


def _format_errors_text(errors: List[ErrorLog]) -> str:
    lines = ["Errors:"]
    lines.extend(f"{error.company_name}: {error.error_message}" for error in errors)
    return "\n".join(lines)


def _format_errors_html(errors: List[ErrorLog]) -> str:
    items = "".join(
        f"<li><b>{escape(error.company_name)}</b>: {escape(error.error_message)}</li>"
        for error in errors
    )
    return f"<p><b>Errors</b></p><ul>{items}</ul>"


def format_digest_preview(jobs: List[Job], errors: List[ErrorLog]) -> Tuple[str, str]:
    """Return (subject, text_body) for a digest, without needing an EmailConfig."""
    subject = f"JobWatch: {len(jobs)} new job posting{'s' if len(jobs) != 1 else ''}"
    if errors:
        subject += f", {len(errors)} error{'s' if len(errors) != 1 else ''}"

    text_body = _format_digest_text(jobs)
    if errors:
        text_body += "\n\n" + _format_errors_text(errors)

    return subject, text_body


def build_digest_email(jobs: List[Job], errors: List[ErrorLog], email_from: str, email_to: str) -> EmailMessage:
    """Build a single digest email listing every newly found job."""
    subject, text_body = format_digest_preview(jobs, errors)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = email_to

    html_body = _format_digest_html(jobs)
    if errors:
        html_body += _format_errors_html(errors)

    message.set_content(text_body)
    message.add_alternative(f"<html><body>{html_body}</body></html>", subtype="html")
    return message


def send_job_notifications(jobs: List[Job], email_config: EmailConfig, errors: List[ErrorLog] | None = None) -> None:
    """Send a single digest email listing every newly found job and any scrape errors for this cycle."""
    errors = errors or []
    if not jobs and not errors:
        return

    message = build_digest_email(jobs, errors, email_config.email_from, email_config.email_to)

    with smtplib.SMTP(email_config.smtp_host, email_config.smtp_port) as server:
        server.starttls()
        server.login(email_config.smtp_username, email_config.smtp_password)
        server.send_message(message)
