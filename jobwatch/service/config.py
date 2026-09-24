import os
from dataclasses import dataclass


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    email_to: str


def load_poll_interval_seconds() -> int:
    try:
        return int(os.getenv("POLL_INTERVAL_SECONDS", "86400"))
    except ValueError:
        raise RuntimeError("POLL_INTERVAL_SECONDS must be an integer") from None


def load_email_config() -> EmailConfig:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_to = os.getenv("EMAIL_TO")
    if not all([smtp_host, smtp_username, smtp_password, email_to]):
        raise RuntimeError(
            "SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_TO environment variables must all be set"
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
        email_to=email_to,
    )
