"""Social media OSINT connector.

Investigates a username/handle across public social platforms. Public/no-login
endpoints are used where they exist (GitHub API + profile page, Reddit's
public JSON, Telegram's public channel pages, YouTube's public channel page).
Platforms that block public enumeration (X/Twitter, Instagram, Facebook,
TikTok) are only checked for a publicly-visible profile page (exists or not),
and are shown with clearly-marked *simulated demo* posts so the UI stays
complete — the connector always remains lawful (public info only).
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import httpx

from app.connectors.base import Connector, ConnectorResult
from app.core.config import REQUEST_TIMEOUT
from app.modules.sentiment import ai_classify_comments, aggregate_comments

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

PROFILE_URLS = {
    "github": "https://github.com/{u}",
    "twitter": "https://x.com/{u}",
    "instagram": "https://www.instagram.com/{u}/",
    "facebook": "https://www.facebook.com/{u}",
    "tiktok": "https://www.tiktok.com/@{u}",
    "youtube": "https://www.youtube.com/@{u}",
    "telegram": "https://t.me/{u}",
    "reddit": "https://www.reddit.com/user/{u}",
    "mastodon": "https://mastodon.social/@{u}",
    "gitlab": "https://gitlab.com/{u}",
    "vk": "https://vk.com/{u}",
    "twitch": "https://www.twitch.tv/{u}",
    "pinterest": "https://www.pinterest.com/{u}",
    "vimeo": "https://vimeo.com/{u}",
    "soundcloud": "https://soundcloud.com/{u}",
    "deviantart": "https://www.deviantart.com/{u}",
}

# Platforms where we fetch real public structured data without login.
LIVE_PLATFORMS = ("github", "gitlab", "reddit", "telegram", "youtube",
                  "mastodon", "twitch", "vk")

# Simplified demo data for platforms that need login to enumerate.
SIMULATED_PLATFORMS = {"twitter", "instagram", "facebook", "tiktok",
                       "pinterest", "vimeo", "deviantart"}


def _probe_platform(platform: str, url: str, handle: str) -> dict:
    entry = {
        "platform": platform,
        "url": url.format(u=handle),
        "handle": handle,
        "exists": False,
    }
    with httpx.Client(timeout=6, headers=HEADERS, follow_redirects=True) as client:
        try:
            resp = client.get(entry["url"])
            entry["exists"] = resp.status_code < 400
        except httpx.HTTPError:
            entry["exists"] = None
            entry["error"] = "unreachable"
            return entry

        if platform in LIVE_PLATFORMS and entry["exists"]:
            try:
                entry.update(LIVE_FETCHERS[platform](client, handle))
            except Exception as exc:
                entry["error"] = f"collection failed: {exc}"
        elif entry["exists"] and platform in SIMULATED_PLATFORMS:
            # Blocked platforms: try a real public web search for mentions of
            # the handle; only fall back to clearly-labelled demo posts if the
            # search finds nothing.
            mentions = _web_search_mentions(handle, platform)
            if mentions:
                entry.update(_platform_mentions(handle, platform, mentions))
            else:
                entry.update(_simulated_posts(handle, platform))
        elif entry["exists"] and platform not in LIVE_PLATFORMS:
            # Extra platforms: just report existence (public profile page).
            entry["public"] = True
            entry["simulated"] = False
    return entry


class SocialMediaConnector(Connector):
    name = "social_media"
    source = "social"

    def query_conf(self, indicator_type: str, value: str) -> ConnectorResult:
        if indicator_type not in ("username", "url"):
            raise ValueError("social_media wants a username or a social URL")
        handle = _extract_handle(indicator_type, value)
        platforms = self._investigate(handle)
        analysis = analyze_social_comments(platforms)
        return ConnectorResult(
            name=self.name,
            query=value,
            value={"handle": handle, "platforms": platforms,
                   "analysis": analysis},
            source=self.source,
            confidence=0.6 if platforms else 0.1,
            evidence_count=analysis.get("total", 0),
        )

    def _investigate(self, handle: str) -> list[dict]:
        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_probe_platform, platform, url, handle):
                       platform for platform, url in PROFILE_URLS.items()}
            for fut in as_completed(futures):
                entry = fut.result()
                results.append(entry)
        results.sort(key=lambda e: list(PROFILE_URLS).index(e["platform"]))
        return results


# ------------------------- live public fetchers ---------------------------

def _fetch_github(client: httpx.Client, handle: str) -> dict:
    api_headers = {"User-Agent": "Hamrabi/0.1 (OSINT; public data only)"}
    resp = client.get(f"https://api.github.com/users/{handle}", headers=api_headers)
    if resp.status_code != 200:
        return {}
    u = resp.json()
    repos = []
    try:
        r2 = client.get(
            f"https://api.github.com/users/{handle}/repos"
            f"?sort=updated&per_page=5", headers=api_headers, timeout=6)
        if r2.status_code == 200:
            repos = [
                {"name": x.get("full_name"), "language": x.get("language"),
                 "stars": x.get("stargazers_count", 0),
                 "forks": x.get("forks_count", 0),
                 "updated": (x.get("updated_at") or "")[:10],
                 "url": x.get("html_url")}
                for x in r2.json()[:5]
            ]
    except Exception:
        pass
    return {
        "public": True,
        "simulated": False,
        "publisher": u.get("name") or handle,
        "handle": handle,
        "location": u.get("location"),
        "joined": u.get("created_at"),
        "followers": u.get("followers", 0),
        "following": u.get("following", 0),
        "public_repos": u.get("public_repos", 0),
        "avatar": u.get("avatar_url"),
        "bio": u.get("bio"),
        "repos": repos,
        "posts_url": u.get("html_url") or PROFILE_URLS["github"].format(u=handle),
    }


def _fetch_reddit(client: httpx.Client, handle: str) -> dict:
    headers = {
        "User-Agent": "Hamrabi/0.1 (OSINT research; public JSON only; contact none)"}
    resp = client.get(f"https://www.reddit.com/user/{handle}/about.json",
                      headers=headers)
    if resp.status_code != 200:
        return {}
    data = resp.json().get("data", {})
    sub = data.get("subreddit") if isinstance(data.get("subreddit"), dict) else {}
    created = data.get("created_utc", 0)
    return {
        "public": True,
        "simulated": False,
        "publisher": data.get("name") or handle,
        "handle": handle,
        "location": sub.get("title"),
        "joined": (datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                   if created else None),
        "karma": data.get("total_karma", 0),
        "followers": sub.get("subscribers", 0),
        "bio": sub.get("description"),
        "posts_url": f"https://www.reddit.com/user/{handle}",
    }


def _fetch_telegram(client: httpx.Client, handle: str) -> dict:
    resp = client.get(f"https://t.me/s/{handle}")
    if resp.status_code != 200:
        return {}
    html = resp.text
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = m.group(1).strip() if m else handle
    bodies = re.findall(r'<span dir="auto"[^>]*>(.*?)</span>', html[:8000], re.S)
    texts = [re.sub(r"<[^>]+>", "", b).strip() for b in bodies]
    texts = [t for t in texts if t]
    return {
        "public": True,
        "simulated": False,
        "publisher": title,
        "handle": handle,
        "location": None,
        "payloads": texts[:6],
        "posts_count": len(texts),
        "posts_url": f"https://t.me/s/{handle}",
    }


def _fetch_gitlab(client: httpx.Client, handle: str) -> dict:
    api_headers = {"User-Agent": "Hamrabi/0.1 (OSINT; public data only)"}
    resp = client.get(f"https://gitlab.com/api/v4/users?username={handle}",
                      headers=api_headers)
    users = resp.json() if resp.status_code == 200 else []
    if not users:
        return {}
    u = users[0]
    return {
        "public": True,
        "simulated": False,
        "publisher": u.get("name") or handle,
        "handle": handle,
        "location": u.get("location"),
        "joined": u.get("created_at"),
        "followers": 0,
        "public_repos": 0,
        "avatar": u.get("avatar_url"),
        "bio": u.get("bio") or u.get("website_url"),
        "posts_url": u.get("web_url") or PROFILE_URLS["gitlab"].format(u=handle),
    }


def _fetch_mastodon(client: httpx.Client, handle: str) -> dict:
    resp = client.get(f"https://mastodon.social/api/v1/accounts/lookup"
                      f"?acct={handle}")
    if resp.status_code != 200:
        return {}
    u = resp.json()
    return {
        "public": True,
        "simulated": False,
        "publisher": u.get("display_name") or u.get("username") or handle,
        "handle": handle,
        "location": (u.get("note") or "")[:160],
        "joined": u.get("created_at"),
        "followers": u.get("followers_count", 0),
        "following": u.get("following_count", 0),
        "posts_count": u.get("statuses_count", 0),
        "avatar": u.get("avatar"),
        "bio": (u.get("note") or "")[:240],
        "posts_url": u.get("url") or PROFILE_URLS["mastodon"].format(u=handle),
    }


def _fetch_twitch(client: httpx.Client, handle: str) -> dict:
    html = client.get(f"https://www.twitch.tv/{handle}").text
    title = _meta_content(html, "property", "og:title")
    return {
        "public": True,
        "simulated": False,
        "publisher": title or handle,
        "handle": handle,
        "location": None,
        "posts_url": f"https://www.twitch.tv/{handle}",
    }


def _fetch_vk(client: httpx.Client, handle: str) -> dict:
    html = client.get(f"https://vk.com/{handle}").text
    title = _meta_content(html, "property", "og:title")
    return {
        "public": True,
        "simulated": False,
        "publisher": title or handle,
        "handle": handle,
        "location": None,
        "posts_url": PROFILE_URLS["vk"].format(u=handle),
    }


def _fetch_youtube(client: httpx.Client, handle: str) -> dict:
    html = client.get(f"https://www.youtube.com/@{handle}").text
    title = (_meta_content(html, "name", "title")
             or _meta_content(html, "property", "og:title"))
    avatar = _meta_content(html, "property", "og:image")
    return {
        "public": True,
        "simulated": False,
        "publisher": title or handle,
        "handle": handle,
        "location": None,
        "avatar": avatar,
        "posts_url": f"https://www.youtube.com/@{handle}",
    }


LIVE_FETCHERS = {
    "github": _fetch_github,
    "gitlab": _fetch_gitlab,
    "reddit": _fetch_reddit,
    "telegram": _fetch_telegram,
    "youtube": _fetch_youtube,
    "mastodon": _fetch_mastodon,
    "twitch": _fetch_twitch,
    "vk": _fetch_vk,
}


# ------------------------- public web-search mentions ----------------------

def _web_search_mentions(handle: str, platform: str) -> list[dict]:
    """Search public DuckDuckGo HTML for real mentions of the handle on the
    platform. Gives real links/titles instead of invented posts."""
    query = _quote(f'"{handle}" {_search_hint(platform)}')
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        with httpx.Client(timeout=6, headers=HEADERS, follow_redirects=False) as c:
            resp = c.get(url, timeout=6)
            if resp.status_code != 200:
                return []
            return _parse_ddg_results(resp.text)[:8]
    except httpx.HTTPError:
        return []


def _search_hint(platform: str) -> str:
    hints = {
        "twitter": "twitter.com:x.com",
        "instagram": "instagram.com",
        "facebook": "facebook.com",
        "tiktok": "tiktok.com",
        "pinterest": "pinterest.com",
        "vimeo": "vimeo.com",
        "deviantart": "deviantart.com",
    }
    return hints.get(platform, platform)


def _quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote_plus(s)


def _parse_ddg_results(html: str) -> list[dict]:
    import urllib.parse
    out = []
    for m in re.finditer(
            r'<a[^>]+class="result__a"[^>]+href="([^"]*)"[^>]*>(.*?)</a>',
            html, re.S):
        url, title = m.group(1), m.group(2)
        if "uddg=" in url:
            url = urllib.parse.unquote(url.split("uddg=", 1)[1].split("&", 1)[0])
        out.append({"title": _strip_html(title)[:140], "url": url})
        if len(out) >= 8:
            break
    return out


def _strip_html(s: str) -> str:
    import html as _html
    return re.sub(r"\s+", " ",
                  _html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def _platform_mentions(handle: str, platform: str, mentions: list[dict]) -> dict:
    return {
        "public": True,
        "simulated": False,
        "web_mentions": True,
        "publisher": handle,
        "handle": handle,
        "location": None,
        "posts": [
            {"text": m["title"], "url": m["url"], "published_at": None,
             "like_count": None, "comment_count": None, "shares": None,
             "comments": []}
            for m in mentions
        ],
        "posts_count": len(mentions),
        "posts_url": PROFILE_URLS.get(platform, "").format(u=handle),
    }


def _meta_content(html: str, attr: str, name: str) -> str | None:
    pattern = re.compile(
        rf'<meta[^>]+\b{re.escape(attr)}="{re.escape(_meta_escape(name))}"'
        rf'[^>]+content="([^"]*)"'
    )
    m = pattern.search(html)
    return m.group(1) if m else None


def _meta_escape(name: str) -> str:
    return name.replace(":", "\\:")


# ------------------------- simulated (demo) data ---------------------------

def _simulated_posts(handle: str, platform: str) -> dict:
    """Clearly-marked demo posts for platforms without a public API."""
    cities = ["Riyadh", "Cairo", "Amman", "Dubai", "London", "Istanbul"]
    pools = {
        "twitter": [
            ("Public posts mention {h} — this demo illustrates the fields the "
             "connector would return with an authenticated collector.", 3, 1),
            ("Thread conversation including {h}.", 7, 0),
        ],
        "instagram": [
            ("Photo post with pinned location. Profile is public.", 12, 2),
            ("Story highlight featuring {h}.", 5, 1),
        ],
        "facebook": [
            ("Public page post with reactions mentioning {h}.", 9, 3),
            ("Shared link post located near the page's metro area.", 4, 0),
        ],
        "tiktok": [
            ("Public video mention of #{h} with comments and shares.", 15, 4),
            ("Short caption mentioning {h}.", 6, 0),
        ],
    }
    posts = []
    base = datetime.now(timezone.utc)
    for i, (text, likes, comments) in enumerate(pools.get(platform, [])):
        post = {
            "public": True,
            "simulated": True,
            "publisher": handle,
            "handle": handle,
            "published_at": (base - timedelta(hours=i * 3)).isoformat(),
            "location": cities[i % len(cities)],
            "like_count": likes,
            "comment_count": likes + comments,
            "shares": 2,
            "text": text.format(h=handle),
            "image": None,
        }
        post["comments"] = [
            {"text": c, "sentiment": None, "score": None, "lang": None}
            for c in _demo_comments(i)
        ]
        posts.append(post)
    return {
        "public": True,
        "simulated": True,
        "publisher": handle,
        "location": "Demo",
        "payloads": [],
        "posts": posts,
        "posts_count": len(posts),
        "posts_url": PROFILE_URLS.get(platform, "").format(u=handle),
    }


def _demo_comments(i: int) -> list[str]:
    pool = [
        "Amazing work, keep it up!",
        "هذا حساب مؤثر وموثوق",
        "Nice, but it could be faster.",
        "مش جيد، الخدمة سيئة",
        "Love the content, recommended.",
        "ما فيه دليل كافي",
        "Great job bro!",
        "معلومات ناقصة",
        "Excellent. Please more!",
        "لا تنشرها، ضعيفة",
    ]
    start = i * 3 % len(pool)
    return pool[start:start + 3]


def _extract_handle(indicator_type: str, value: str) -> str:
    value = value.strip().strip("/")
    if indicator_type == "url":
        value = value.split("/")[-1]
    return value.lstrip("@").strip().lower() or "unknown"


# ------------------------- comment analysis -------------------------------

def analyze_social_comments(platforms: list[dict]) -> dict:
    """Collect + classify comments found across the platform entries."""
    comments: list[str] = []
    for entry in platforms or []:
        payloads = entry.get("posts") or entry.get("payloads") or []
        for p in payloads:
            if isinstance(p, str):
                comments.append(p)
            elif isinstance(p, dict):
                for c in p.get("comments") or []:
                    if isinstance(c, str):
                        comments.append(c)
                    elif isinstance(c, dict) and c.get("text"):
                        comments.append(c["text"])

    if not comments:
        return {"comments": [], "counts": {"positive": 0, "negative": 0,
                "neutral": 0}, "total": 0, "good_ratio": 0.0, "bad_ratio": 0.0,
                "provider": "rules"}

    ai = ai_classify_comments(comments)
    return ai or aggregate_comments(comments)