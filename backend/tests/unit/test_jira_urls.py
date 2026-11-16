"""URL do site Jira (F04-RT-03): só https://<site>.atlassian.net, contra SSRF."""

import pytest

from app.integrations.jira.urls import InvalidSiteUrlError, normalize_site_url

pytestmark = pytest.mark.req("F04-RT-03")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://acme.atlassian.net", "https://acme.atlassian.net"),
        ("  https://Acme.Atlassian.net/  ", "https://acme.atlassian.net"),
        (
            "https://acme-br.atlassian.net/jira/software/projects?x=1#y",
            "https://acme-br.atlassian.net",
        ),
    ],
)
def test_urls_aceitas_sao_normalizadas(raw: str, expected: str) -> None:
    assert normalize_site_url(raw) == expected


@pytest.mark.req("F04-RF-03")
@pytest.mark.parametrize(
    "raw",
    [
        "http://169.254.169.254",
        "http://acme.atlassian.net",
        "https://169.254.169.254",
        "https://localhost",
        "https://atlassian.net",
        "https://acme.atlassian.net.evil.com",
        "https://evil.com/acme.atlassian.net",
        "https://acme.atlassian.net:8443",
        "https://user:pass@acme.atlassian.net",
        "https://a.b.atlassian.net",
        "https://-acme.atlassian.net",
        "acme.atlassian.net",
        "ftp://acme.atlassian.net",
        "https://acme.atlassian.net:abc",
        "",
    ],
)
def test_urls_fora_do_padrao_sao_recusadas(raw: str) -> None:
    with pytest.raises(InvalidSiteUrlError):
        normalize_site_url(raw)
