import ipaddress
import re

IP_RE = re.compile(r"(?<!\d)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d)")
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}\b")
DOMAIN_RE = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}\b")
URL_RE = re.compile(r"https?://(?:[^\s\"'<>]|/)+")
USERNAME_RE = re.compile(r"(?<![\w@])@([a-zA-Z0-9_.-]{2,30})\b")

ALIAS_TYPES = {
    "text": "text",
    "email": "email",
    "domain": "domain",
    "ip": "ip",
    "url": "url",
    "username": "username",
    "phone": "phone",
    "keyword": "keyword",
}

DOMAIN_TLDS = {
    "com", "net", "org", "io", "dev", "me", "co", "info", "biz", "xyz",
    "online", "site", "tech", "app", "guru", "ai", "sa", "ae", "eg",
    "com.sa", "com.ae", "co.za", "org.uk",
}


def _valid_ip(candidate: str) -> bool:
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False


def _is_known_tld(domain: str) -> bool:
    tld = domain.rsplit(".", 1)[-1].lower()
    return tld in DOMAIN_TLDS


def extract_entities(text: str) -> list[dict]:
    """Extract indicators from free text and return [{"type", "value"}...] (deduplicated)."""
    seen: set = set()
    result: list[dict] = []

    def add(kind: str, value: str):
        key = f"{kind}:{value.lower()}"
        if key not in seen:
            seen.add(key)
            result.append({"type": kind, "value": value})

    for m in EMAIL_RE.finditer(text):
        add("email", m.group(0))
        domain = m.group(0).split("@", 1)[1]
        if domain and _is_known_tld(domain):
            add("domain", domain)

    for m in URL_RE.finditer(text):
        add("url", m.group(0))

    for m in IP_RE.finditer(text):
        if _valid_ip(m.group(1)):
            add("ip", m.group(1))

    for m in DOMAIN_RE.finditer(text):
        if _is_known_tld(m.group(0)):
            add("domain", m.group(0))

    for m in USERNAME_RE.finditer(text):
        add("username", m.group(1))

    return result


def normalize(value: str) -> str:
    return value.strip().lower()