import os
from dataclasses import dataclass


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    email_to: list[str]


def load_poll_interval_seconds() -> int:
    try:
        return int(os.getenv("POLL_INTERVAL_SECONDS", "86400"))
    except ValueError:
        raise RuntimeError("POLL_INTERVAL_SECONDS must be an integer") from None


def load_max_concurrent_company_scrapes() -> int:
    raw_value = os.getenv("MAX_CONCURRENT_COMPANY_SCRAPES", "10")
    try:
        value = int(raw_value)
    except ValueError:
        raise RuntimeError(
            "MAX_CONCURRENT_COMPANY_SCRAPES must be a positive integer"
        ) from None
    if value <= 0:
        raise RuntimeError(
            "MAX_CONCURRENT_COMPANY_SCRAPES must be a positive integer"
        )
    return value


def load_email_config() -> EmailConfig:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_to = os.getenv("EMAIL_TO")
    if not all([smtp_host, smtp_username, smtp_password]):
        raise RuntimeError(
            "SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD environment variables must all be set"
        )
    if email_to is None or not email_to.strip():
        raise RuntimeError("EMAIL_TO must contain at least one recipient email address")
    email_recipients = [address.strip() for address in email_to.split(",")]
    if any(not address for address in email_recipients):
        raise RuntimeError(
            "EMAIL_TO must contain comma-separated email addresses with no empty entries"
        )
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        raise RuntimeError("SMTP_PORT must be an integer") from None

    return EmailConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        email_from=os.getenv("EMAIL_FROM", smtp_username),
        email_to=email_recipients,
    )
