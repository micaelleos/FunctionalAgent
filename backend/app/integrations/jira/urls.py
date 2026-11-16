"""Validação da URL do site Jira (F04-RT-03): só `https://<site>.atlassian.net`, contra SSRF."""

import re
from urllib.parse import urlsplit

_SITE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.atlassian\.net$")


class InvalidSiteUrlError(ValueError):
    pass


def normalize_site_url(raw: str) -> str:
    """Devolve `https://<site>.atlassian.net`; descarta o caminho colado (ex.: `/jira/software`)."""
    value = raw.strip()
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise InvalidSiteUrlError(raw) from exc
    host = (parts.hostname or "").lower()
    if (
        parts.scheme.lower() != "https"
        or parts.username is not None
        or parts.password is not None
        or port is not None
        or not _SITE.match(host)
    ):
        raise InvalidSiteUrlError(raw)
    return f"https://{host}"
