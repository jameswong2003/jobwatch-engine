from types import SimpleNamespace

from jobwatch.service.email_client import build_digest_email, format_digest_preview


def make_job(company_name, title, url):
    return SimpleNamespace(
        company=SimpleNamespace(company_name=company_name),
        job_title=title,
        job_posting_url=url,
    )


def test_digest_groups_plain_text_jobs_by_company():
    jobs = [
        make_job("Acme", "Backend Engineer", "https://jobs.example/1"),
        make_job("Other Co", "Designer", "https://jobs.example/2"),
        make_job("Acme", "SRE", "https://jobs.example/3"),
    ]

    subject, body = format_digest_preview(jobs, [])

    assert subject == "JobWatch: 3 new job postings"
    assert body == (
        "Acme\nBackend Engineer --- https://jobs.example/1\nSRE --- https://jobs.example/3"
        "\n\nOther Co\nDesigner --- https://jobs.example/2"
    )


def test_digest_html_escapes_external_company_title_and_url_text():
    job = make_job('R&D <Group>', 'Engineer <script>alert("x")</script>', 'https://jobs.example/?a=1&b="2"')

    message = build_digest_email([job], [], "jobs@example.com", "user@example.com")
    html = message.get_body(preferencelist=("html",)).get_content()

    assert "R&amp;D &lt;Group&gt;" in html
    assert "Engineer &lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in html
    assert "?a=1&amp;b=&quot;2&quot;" in html
    assert message["To"] == "user@example.com"


def test_digest_subject_reports_errors_even_without_jobs():
    error = SimpleNamespace(company_name="Acme", error_message="board unavailable")

    subject, body = format_digest_preview([], [error])

    assert subject == "JobWatch: 0 new job postings, 1 error"
    assert "Acme: board unavailable" in body
