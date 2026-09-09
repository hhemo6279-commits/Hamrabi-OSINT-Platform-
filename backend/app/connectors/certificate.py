"""TLS/Certificate connector — reads the public TLS certificate presented
by a domain over a standard TLS handshake. No scan, no exploit: just a
normal HTTPS (sometimes port 443) connection reported publicly.
"""
import ssl
import socket
from datetime import datetime, timezone

from app.connectors.base import Connector, ConnectorResult

TIMEOUT = 8
CONTEXT = ssl.create_default_context()


class CertificateConnector(Connector):
    name = "certificate"
    source = "certificate"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("domain", "url"):
            raise ValueError("certificate only supports domains/urls")
        from app.connectors.dns import host_from_url
        host = host_from_url(value) if indicator_type == "url" else value
        return self._cert(host)

    @staticmethod
    def _cert(host: str) -> ConnectorResult:
        try:
            with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
                with CONTEXT.wrap_socket(sock, server_hostname=host) as tls:
                    cert = tls.getpeercert()
        except OSError as exc:
            return ConnectorResult(
                name="certificate", query=host, value={}, source="certificate",
                confidence=0.0, evidence_count=0, error=str(exc),
            )

        data = {
            "hostname": host,
            "subject": _common_name(cert.get("subject", [])),
            "issuer": _common_name(cert.get("issuer", [])),
            "notBefore": cert.get("notBefore"),
            "notAfter": cert.get("notAfter"),
            "serial": cert.get("serialNumber"),
        }
        # SANs are the useful public data point
        san = []
        for item in cert.get("subjectAltName", []):
            san.append(item[1])
        data["sans"] = san

        return ConnectorResult(
            name="certificate", query=host, value=data, source="certificate",
            confidence=0.85 if data else 0.0,
            evidence_count=1 + len(san),
        )


def _common_name(items) -> str | None:
    """Extract the CN from a certificate field list (e.g. subject / issuer)."""
    for entry in items:
        for oid, value in entry:
            if oid == "commonName":
                return value
    return None


def _sans(cert) -> str | None:
    return _common_name(cert.get("subject", []))


def tls_scan_from_host(host: str) -> dict:
    """Helper used by report generator."""
    res = CertificateConnector()._cert(host)
    return res.value