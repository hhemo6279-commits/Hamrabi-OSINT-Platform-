"""WHOIS connector — pulls public registry records for a domain.

Implements a lightweight WHOIS query directly over the standard TCP 43
protocol so the skeleton does not depend on a fragile third-party WHOIS
parser. Results are kept non-sensitive (public registration data only).
"""
import socket
from datetime import datetime, timezone

from app.connectors.base import Connector, ConnectorResult

WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
    "io": "whois.nic.io",
}

TIMEOUT = 8
MAX_RESPONSE = 1024 * 64


class WhoisConnector(Connector):
    name = "whois"
    source = "whois"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("domain", "url"):
            raise ValueError("whois only supports domains")
        from app.connectors.dns import host_from_url
        host = host_from_url(value) if indicator_type == "url" else value
        return self._whois(host)

    def _whois(self, domain: str) -> ConnectorResult:
        server = self._pick_server(domain)
        if server is None:
            return ConnectorResult(
                name=self.name, query=domain, value={}, source=self.source,
                confidence=0.0, evidence_count=0, error="no whois server mapped",
            )
        try:
            data = self._query(server, domain)
        except OSError as exc:
            return ConnectorResult(
                name=self.name, query=domain, value={}, source=self.source,
                confidence=0.0, evidence_count=0, error=str(exc),
            )
        parsed = self._parse(data)
        return ConnectorResult(
            name=self.name, query=domain, value=parsed, source=self.source,
            confidence=0.8 if parsed else 0.0, evidence_count=1 if parsed else 0,
        )

    @staticmethod
    def _pick_server(domain: str) -> str | None:
        tld = domain.rsplit(".", 1)[-1].lower()
        return WHOIS_SERVERS.get(tld)

    @staticmethod
    def _query(server: str, domain: str) -> str:
        with socket.create_connection((server, 43), timeout=TIMEOUT) as sock:
            sock.sendall((domain + "\r\n").encode())
            chunks = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(len(c) for c in chunks) > MAX_RESPONSE:
                    break
        return b"".join(chunks).decode("utf-8", errors="replace")

    @staticmethod
    def _parse(raw: str) -> dict:
        wanted = {
            "Registrant Organization": "registrant_org",
            "Registrant Org": "registrant_org",
            "Registrant State/Province": "registrant_state",
            "Registrant State": "registrant_state",
            "Registrant Country": "registrant_country",
            "Registrant City": "registrant_city",
            "Registrant Postal Code": "registrant_postal",
            "Registrant Street": "registrant_street",
            "Registrar": "registrar",
            "Registrar WHOIS Server": "whois_server",
            "Creation Date": "created",
            "Updated Date": "updated",
            "Registry Expiry Date": "expiry",
            "Name Server": "nameservers",
        }
        result: dict = {}
        nameservers = []
        for line in raw.splitlines():
            stripped = line.strip()
            for key, alias in wanted.items():
                if stripped.startswith(key + ":"):
                    value = stripped.split(":", 1)[1].strip()
                    if alias == "nameservers":
                        if value:
                            nameservers.append(value)
                    elif alias not in result:
                        result[alias] = value
        # Verisign "Name Server" lines repeat; keep batch of them together.
        result.setdefault("created", "")
        if nameservers:
            result["nameservers"] = nameservers[:8]
        # Kill empty holders
        for k in ("created",):
            if k in result and not result[k]:
                del result[k]
        return result