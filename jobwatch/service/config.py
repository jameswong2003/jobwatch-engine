import os


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
