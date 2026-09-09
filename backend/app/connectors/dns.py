"""
DNS connector — collects public DNS records for a domain or reverse lookup
for an IP address. Uses only standard DNS queries (no brute force / no
attacks, purely public data).
"""
import socket

from app.connectors.base import Connector, ConnectorResult

try:
    import dns.resolver
    import dns.reversename
    DNS_AVAILABLE = True
except ImportError:  # pragma: no cover
    DNS_AVAILABLE = False

RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA")


class DnsConnector(Connector):
    name = "dns"
    source = "dns"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if not DNS_AVAILABLE:
            raise RuntimeError("dnspython not installed")

        if indicator_type == "ip":
            return self._reverse(value)
        if indicator_type in ("domain", "url"):
            host = _host_from_url(value) if indicator_type == "url" else value
            return self._forward(host)
        raise ValueError(f"unsupported indicator type: {indicator_type}")

    def _forward(self, host: str) -> ConnectorResult:
        records: dict[str, list[str]] = {}
        for rtype in RECORD_TYPES:
            try:
                answers = dns.resolver.resolve(host, rtype)
            except dns.resolver.NoAnswer:
                continue
            except dns.resolver.NXDOMAIN:
                return ConnectorResult(
                    name=self.name, query=host, value={"nxdomain": True},
                    source=self.source, confidence=1.0, evidence_count=1,
                )
            except Exception:
                continue
            records[rtype] = [a.to_text().strip('"') for a in answers]
        count = sum(len(v) for v in records.values())
        return ConnectorResult(
            name=self.name, query=host, value={"records": records},
            source=self.source, confidence=0.9 if count else 0.0,
            evidence_count=count,
        )

    def _reverse(self, ip: str) -> ConnectorResult:
        try:
            ptr = dns.reversename.from_address(ip)
            answers = dns.resolver.resolve(ptr, "PTR")
        except Exception:
            return ConnectorResult(
                name=self.name, query=ip, value={}, source=self.source,
                confidence=0.0, evidence_count=0,
            )
        ptrs = [a.to_text() for a in answers]
        return ConnectorResult(
            name=self.name, query=ip, value={"ptr": ptrs}, source=self.source,
            confidence=0.85 if ptrs else 0.0, evidence_count=len(ptrs),
        )


def _host_from_url(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).hostname or url


def host_from_url(url: str) -> str:
    return _host_from_url(url)