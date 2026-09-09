import re

from app.modules.entity_extraction import extract_entities


def sanitize(raw: str) -> str:
    """Strip control chars and HTML tags (XSS/CRLF hygiene)."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", raw)
    cleaned = re.sub(r"<[^>]*>", "", cleaned)
    return cleaned.strip()


IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,63}$")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,32}$")
DOMAIN_RE = re.compile(r"^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}$")


def classify_input(raw: str) -> str:
    value = raw.strip()
    if not value:
        return "empty"

    if " " not in value:
        if IP_RE.match(value) and all(0 <= int(octet) <= 255 for octet in value.split(".")):
            return "ip"
        if EMAIL_RE.match(value):
            return "email"
        if URL_RE.match(value):
            return "url"
        if DOMAIN_RE.match(value):
            return "domain"
        if USERNAME_RE.match(value) and ("_" in value or "-" in value or "." in value):
            return "username"
        if USERNAME_RE.match(value) and " " not in value:
            return "username"

    return "text"


def primary_entities(raw: str) -> list[dict]:
    """Returns [{"type": ..., "value": ...}] for the main indicator of the raw input.

    For URLs we also emit the host domain as a separate entity so that WHOIS,
    DNS, certificate and subdomain connectors all run on the site — giving
    registration date, location and hosting info for the link.
    """
    value = raw.strip()
    kind = classify_input(value)
    if kind == "url":
        host = _host_from_url(value)
        result = [{"type": "url", "value": value}]
        if host:
            result.append({"type": "domain", "value": host})
        return result
    if kind in ("email", "domain", "ip", "username"):
        return [{"type": kind, "value": value}]
    return extract_entities(value)


def _host_from_url(url: str) -> str | None:
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host and "." in host:
        return host
    return None