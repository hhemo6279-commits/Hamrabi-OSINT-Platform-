"""Page analyzer connector — fetches a URL's real content and extracts the
rich, human-visible OSINT facts: publication time, author, geo/location,
open-graph & twitter metadata, canonical/redirect chain, links, social
handles and keywords.

Thin standard-library HTML parsing (html.parser) so no heavy deps.
"""
from __future__ import annotations

import html as _html
import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.connectors.base import Connector, ConnectorResult
from app.core.config import REQUEST_TIMEOUT

PAGE_SIZE_LIMIT = 2 * 1024 * 1024  # 2 MB cap

SOCIAL_HOSTS = {
    "x.com": "X", "twitter.com": "X", "facebook.com": "Facebook",
    "instagram.com": "Instagram", "tiktok.com": "TikTok",
    "youtube.com": "YouTube", "youtu.be": "YouTube",
    "t.me": "Telegram", "telegram.org": "Telegram",
    "linkedin.com": "LinkedIn", "wa.me": "WhatsApp",
}

DATE_PATTERNS = [
    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
    "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y",
    "%B %d, %Y", "%d %B %Y", "%Y/%m/%d",
]


class _MetaParser(HTMLParser):
    """Collect meta tags, og/twitter props, title, canonical and links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.metas: dict[str, str] = {}
        self.props: dict[str, str] = {}
        self.canonical = ""
        self.links: list[str] = []
        self.visible: list[str] = []
        self.jsonld: list[str] = []
        self._jsonld = False
        self._jsonld_text = None
        self._in_title = False
        self._skip_depth = 0

    SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "nav", "footer"}
    JSONLD_TAG = "application/ld+json"

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "script" and a.get("type") == self.JSONLD_TAG:
            self._jsonld = True
            self._jsonld_text = ""
        elif tag == "meta":
            if a.get("name"):
                self.metas.setdefault(a["name"].strip().lower(),
                                      a.get("content", "").strip())
            if a.get("property"):
                self.props.setdefault(a["property"].strip().lower(),
                                      a.get("content", "").strip())
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "canonical" in rel:
                self.canonical = a.get("href", "")
            href = a.get("href")
            if href:
                self.links.append(href)
        elif tag == "a":
            href = a.get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and getattr(self, "_jsonld", False) and \
                self._jsonld_text is not None:
            self.jsonld = self.jsonld + [self._jsonld_text]
            self._jsonld = False
            self._jsonld_text = None
        elif tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif getattr(self, "_jsonld", False) and self._jsonld_text is not None:
            self._jsonld_text += data
        elif self._skip_depth == 0:
            d = data.strip()
            if d:
                self.visible.append(data)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(text or "")).strip()


def _first(*values) -> str:
    for v in values:
        if v:
            return v
    return ""


def _parse_date(raw: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip().strip('"')
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except (ValueError, TypeError):
            continue
    return None


def _social_of(link: str) -> str:
    host = urlparse(link).netloc.lower()
    for key, label in SOCIAL_HOSTS.items():
        if host == key or host.endswith("." + key):
            return label
    return ""


def _jsonld_facts(parser: _MetaParser) -> dict:
    """Pull published/modified/author/location from structured data (JSON-LD)."""
    import json as _json

    out: dict = {}
    for blob in getattr(parser, "jsonld", []) or []:
        try:
            data = _json.loads(blob)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for node in items:
            if not isinstance(node, dict):
                continue
            types = node.get("@type", "")
            types = [types] if isinstance(types, str) else types
            type_str = " ".join(str(x) for x in types).lower()
            if not any(t in type_str for t in ("article", "newsarticle", "blogposting",
                                               "report", "webpage", "creativework")):
                continue
            if not out.get("published_time") and node.get("datePublished"):
                out["published_time"] = _parse_date(str(node["datePublished"])) or ""
            if not out.get("modified_time") and node.get("dateModified"):
                out["modified_time"] = _parse_date(str(node["dateModified"])) or ""
            if not out.get("author"):
                a = node.get("author")
                if isinstance(a, dict):
                    out["author"] = _clean(str(a.get("name", "")))
                elif isinstance(a, list) and a:
                    first = a[0]
                    out["author"] = _clean(str(first.get("name", ""))) \
                        if isinstance(first, dict) else _clean(str(first))
        if out.get("published_time"):
            out["published_time_source"] = "json-ld"
    return out


def _host_meta(parser: _MetaParser, host: str) -> dict:
    raw_date = _first(
        parser.props.get("article:published_time"),
        parser.props.get("og:article:published_time"),
        parser.props.get("og:published_time"),
        parser.metas.get("date"),
        parser.metas.get("pubdate"),
        parser.props.get("article:modified_time"),
        parser.props.get("og:updated_time"),
    )
    author = _first(
        parser.props.get("article:author"),
        parser.metas.get("author"),
        parser.props.get("og:article:author"),
    )
    geo = _first(
        parser.props.get("og:location"),
        parser.metas.get("geo.position"),
        parser.metas.get("geo.placename"),
        parser.metas.get("geo.region"),
        parser.props.get("place:location:latitude"),
    )
    report = {
        "host": host,
        "favicon": _favicon(_clean(parser.canonical) or f"https://{host}"),
    }
    # structured data (JSON-LD) is the richest source; merge, prefer explicit meta
    report.update(_jsonld_facts(parser))
    if raw_date:
        report["published_time"] = _parse_date(raw_date) or ""
        report["published_time_source"] = "meta"
    modified = _first(parser.props.get("article:modified_time"),
                      parser.props.get("og:updated_time"))
    if modified:
        report["modified_time"] = _parse_date(modified) or ""
    if author:
        report["author"] = author
    if geo:
        report["geo"] = geo
    if _clean(parser.canonical):
        report["canonical"] = parser.canonical
    return report


def _favicon(base: str) -> str:
    try:
        return urljoin(base, "/favicon.ico")
    except Exception:
        return ""


def _top_social(links: list[str]) -> list[str]:
    seen = set()
    out = []
    for ln in links:
        label = _social_of(ln)
        if label and label not in seen:
            seen.add(label)
            out.append(ln)
    return out


STOPW = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was",
    "been", "have", "has", "will", "not", "what", "when", "about",
    "بعد", "على", "مع", "من", "في", "عن", "هذا", "هذه", "أن", "إلى",
    "لأن", "لكن", "كان", "سيتم", "قال", "وقال", "أعلن", "حققت",
}


def _keywords(text: str) -> list[str]:
    """Frequency-based keyword hints from page text (no external NLP)."""
    if not text:
        return []
    words = re.findall(r"[A-Za-z\u0600-\u06FF]{3,}", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in STOPW and len(w) <= 24:
            freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in ranked[:12]]


class PageConnector(Connector):
    name = "page"
    source = "page"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("url", "domain"):
            raise ValueError("page connector needs a url or domain")
        url = value if re.match(r"^https?://", value, re.IGNORECASE) \
            else f"https://{value}"
        return self._analyze(value, url)

    @staticmethod
    def _analyze(raw: str, url: str) -> ConnectorResult:
        host = urlparse(url).netloc
        text = ""
        final_url = url
        status = 0
        redirs: list[dict] = []
        try:
            with httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT,
                              headers={
                                  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                "Chrome/124.0 Safari/537.36",
                                  "Accept-Language": "en,ar;q=0.9",
                              }) as client:
                resp = client.get(url)
                status = resp.status_code
                final_url = str(resp.url)
                redirs = [
                    {"status": h.status_code,
                     "location": h.headers.get("location", "")}
                    for h in resp.history
                ]
                if status < 400:
                    text = resp.text
                    if len(text) > PAGE_SIZE_LIMIT:
                        text = text[:PAGE_SIZE_LIMIT]
                    # skip obviously-non-html
                    if "<" in text and ">" in text:
                        text = text
                    else:
                        text = ""
                    content = text
                else:
                    content = ""
        except httpx.HTTPError as exc:
            return ConnectorResult(
                name="page", query=url, value={"error": str(exc)}, source="page",
                confidence=0.0, evidence_count=0, error=str(exc),
            )

        parser = _MetaParser()
        try:
            parser.feed(content or "")
            parser.close()
        except Exception:
            pass

        title = _clean(parser.title) or _clean(_first(
            parser.props.get("og:title"), parser.metas.get("title")))
        description = _clean(_first(
            parser.metas.get("description"),
            parser.props.get("og:description"),
            parser.metas.get("twitter:description")))

        found_social = _top_social([urljoin(final_url, ln) for ln in parser.links])

        # plain-text scope for keyword extraction
        text_blob = _clean(" ".join(parser.visible))[:3000]
        value = {
            "url": final_url,
            "final_status": status,
            "title": title,
            "description": description,
            "keywords": _keywords(text_blob),
        }
        if redirs:
            value["redirects"] = redirs
        value.update(_host_meta(parser, host))
        if found_social:
            value["social_links"] = found_social
        if text_blob:
            value["text_preview"] = text_blob[:600]

        for k in list(value):
            if value[k] in (None, "", [], {}):
                del value[k]

        evidence = sum(1 for v in value.values() if v)
        return ConnectorResult(
            name="page", query=url, value=value, source="page",
            confidence=0.8 if value else 0.2, evidence_count=evidence,
        )