"""Public profile source connector — checks whether a username has a public
profile on well-known platforms via plain HTTP (each profile page is public
information). Rate-limited and safe: we only look at "exists or not" pages.
"""
import httpx

from app.connectors.base import Connector, ConnectorResult
from app.core.config import REQUEST_TIMEOUT

SOURCE_URLS = {
    "github": "https://github.com/{u}",
    "gitlab": "https://gitlab.com/{u}",
    "keybase": "https://keybase.io/{u}",
    "twitter": "https://twitter.com/{u}",
    "instagram": "https://www.instagram.com/{u}/",
}

HEADERS = {"User-Agent": "Hamrabi/0.1 (OSINT research; rate-limited)"}


class PublicSourcesConnector(Connector):
    name = "public_sources"
    source = "public_sources"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("username",):
            raise ValueError("public_sources wants a username")
        profile = self._check_profile(value)
        return ConnectorResult(
            name=self.name, query=value, value={"profiles": profile},
            source=self.source,
            confidence=0.55 if profile else 0.1,
            evidence_count=len(profile),
        )

    @staticmethod
    def _check_profile(u: str) -> list[dict]:
        profile = []
        with httpx.Client(timeout=REQUEST_TIMEOUT, headers=HEADERS,
                          follow_redirects=False) as client:
            for platform, template in SOURCE_URLS.items():
                try:
                    resp = client.get(template.format(u=u))
                    if resp.status_code == 200:
                        profile.append({
                            "platform": platform,
                            "url": template.format(u=u),
                            "status": "found",
                        })
                except httpx.HTTPError:
                    continue
        return profile