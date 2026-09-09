"""Subdomain connector — discovers public subdomains from Certificate
Transparency logs via crt.sh. This is purely public passive infrastructure
intelligence; it performs no scans and no interaction with the target.
"""
import httpx

from app.connectors.base import Connector, ConnectorResult
from app.core.config import REQUEST_TIMEOUT

CRT_URL = "https://crt.sh/?q={query}&output=json"
HEADERS = {"User-Agent": "Hamrabi/0.1 (OSINT research; public CT logs)"}


class SubdomainConnector(Connector):
    name = "subdomains"
    source = "certificate_transparency"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("domain", "url"):
            raise ValueError("subdomains only supports domains/urls")
        from app.connectors.dns import host_from_url
        host = host_from_url(value) if indicator_type == "url" else value
        return self._ct(host)

    @staticmethod
    def _ct(host: str) -> ConnectorResult:
        q = f"%.{host}"
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT, headers=HEADERS,
                              follow_redirects=True) as client:
                resp = client.get(CRT_URL.format(query=q))
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError):
            return ConnectorResult(
                name="subdomains", query=host, value={"subdomains": []},
                source="certificate_transparency",
                confidence=0.0, evidence_count=0,
                error="crt.sh unreachable or malformed response",
            )

        subdomains = set()
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            names = entry.get("name_value", "")
            for name in names.splitlines():
                name = name.strip().lstrip("*.").lower()
                if name.endswith(host) and name != host:
                    subdomains.add(name)

        order = sorted(subdomains)
        return ConnectorResult(
            name="subdomains", query=host, value={"subdomains": order},
            source="certificate_transparency",
            confidence=0.8 if order else 0.0,
            evidence_count=len(order),
        )