"""HTTP fingerprint connector — gathers public HTTP metadata of a domain
(server header, redirects, common technology fingerprints). Purely a normal
GET request; it never probes or exploits anything.
"""
import re

import httpx

from app.connectors.base import Connector, ConnectorResult
from app.core.config import REQUEST_TIMEOUT

TIMEOUT_KEEP = REQUEST_TIMEOUT

TECH_FINGERPRINTS = {
    "server": {
        "nginx": "nginx", "apache": "Apache", "iis": "Microsoft-IIS",
        "cloudflare": "cloudflare", "caddy": "Caddy", "openresty": "openresty",
    },
    "via": {"varnish": "Varnish", "cloudflare": "cloudflare"},
    "x-powered-by": {"php": "PHP", "asp.net": "ASP.NET", "express": "Express"},
}


class HttpConnector(Connector):
    name = "http"
    source = "http"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("domain", "url", "ip"):
            raise ValueError("http connector needs a domain/url/ip")
        from app.connectors.dns import host_from_url
        host = host_from_url(value) if indicator_type == "url" else value
        return self._fingerprint(value, host)

    @staticmethod
    def _fingerprint(raw: str, host: str) -> ConnectorResult:
        url = raw if re.match(r"^https?://", raw, re.IGNORECASE) \
            else f"https://{host}"
        try:
            with httpx.Client(follow_redirects=True, timeout=TIMEOUT_KEEP,
                              headers={"User-Agent": "Hamrabi/0.1 (OSINT research)"}) as client:
                resp = client.get(url)
        except httpx.HTTPError as exc:
            return ConnectorResult(
                name="http", query=host, value={}, source="http",
                confidence=0.0, evidence_count=0, error=str(exc),
            )

        headers = resp.headers
        redirs = []
        for h, r in resp.history:
            redirs.append({"status": h.status_code, "location": h.headers.get("location", "")})

        value = {
            "url": str(resp.url),
            "status": resp.status_code,
            "server": headers.get("server"),
            "powered_by": headers.get("x-powered-by"),
            "technologies": detect_technologies(headers),
            "redirects": redirs,
            "content_type": headers.get("content-type"),
        }
        count = sum(1 for v in value.values() if v)
        return ConnectorResult(
            name="http", query=host, value=value, source="http",
            confidence=0.7 if count else 0.3, evidence_count=count,
        )


def detect_technologies(headers) -> list[str]:
    found = set()
    server = (headers.get("server") or "").lower()
    for key, mapping in TECH_FINGERPRINTS.items():
        raw = (headers.get(key) or "").lower()
        for token, label in mapping.items():
            if token in raw:
                found.add(f"{label} ({key})")
    if "Cloudflare" in server or "cloudflare" in (headers.get("via") or ""):
        found.add("Cloudflare CDN")
    return sorted(found)