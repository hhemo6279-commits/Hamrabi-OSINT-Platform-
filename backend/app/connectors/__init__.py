"""Connector registry — maps types to connectors so the pipeline can run
sources uniformly while keeping each connector independent."""

from app.connectors.base import Connector


def _load() -> dict[str, list]:
    from app.connectors.certificate import CertificateConnector
    from app.connectors.dns import DnsConnector
    from app.connectors.http import HttpConnector
    from app.connectors.page import PageConnector
    from app.connectors.public_sources import PublicSourcesConnector
    from app.connectors.social import SocialMediaConnector
    from app.connectors.subdomains import SubdomainConnector
    from app.connectors.whois import WhoisConnector

    return {
        "domain": [DnsConnector(), WhoisConnector(), CertificateConnector(),
                   HttpConnector(), PageConnector(), SubdomainConnector()],
        "url": [HttpConnector(), PageConnector(), DnsConnector(),
                CertificateConnector(), SubdomainConnector(), SocialMediaConnector()],
        "ip": [DnsConnector(), HttpConnector()],
        "email": [DnsConnector()],
        "username": [PublicSourcesConnector(), SocialMediaConnector()],
    }


_REGISTRY = _load()


def connectors_for(indicator_type: str) -> list:
    return _REGISTRY.get(indicator_type, [])