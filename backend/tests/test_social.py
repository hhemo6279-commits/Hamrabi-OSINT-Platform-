"""Offline tests for the social-media connector helpers and the multilingual
sentiment engine (no network calls)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.connectors.social import (
    _demo_comments,
    _extract_handle,
    analyze_social_comments,
)
from app.modules.sentiment import aggregate_comments, classify_comment


def test_sentiment_english_positive():
    res = classify_comment("Amazing work, keep it up!")
    assert res["sentiment"] == "positive"
    assert res["lang"] == "en"
    assert res["score"] > 0


def test_sentiment_english_negative():
    res = classify_comment("This is terrible and broken.")
    assert res["sentiment"] == "negative"


def test_sentiment_arabic_positive():
    res = classify_comment("ممتاز شكرا عمل رائع")
    assert res["sentiment"] == "positive"
    assert res["lang"] == "ar"


def test_sentiment_arabic_negative():
    res = classify_comment("مش جيد، الخدمة سيئة")
    assert res["sentiment"] == "negative"


def test_empty_comment_neutral():
    res = classify_comment("")
    assert res["sentiment"] == "neutral"


def test_aggregate_counts_mix():
    agg = aggregate_comments(["Great!", "Bad service", "ok", "رائع"])
    assert agg["counts"]["positive"] == 2
    assert agg["counts"]["negative"] == 1
    assert agg["counts"]["neutral"] == 1
    assert agg["total"] == 4
    assert 0 < agg["good_ratio"] <= 1


def test_social_handle_extraction():
    assert _extract_handle("username", "@alice") == "alice"
    assert _extract_handle("username", "alice") == "alice"
    assert _extract_handle("url", "https://x.com/bob/") == "bob"
    assert _extract_handle("url", "https://www.instagram.com/carol") == "carol"


def test_demo_comments_returns_k3():
    comments = _demo_comments(0)
    assert len(comments) == 3
    assert comments[0]  # non-empty strings


def test_analyze_social_comments_empty():
    out = analyze_social_comments([])
    assert out["total"] == 0
    assert out["provider"] == "rules"


def test_analyze_social_comments_from_posts():
    platforms = [
        {"posts": [{"comments": ["Great!", "bad one", "ممتاز"]}]},
        {"posts": ["neutral phrase"]},
    ]
    out = analyze_social_comments(platforms)
    assert out["total"] == 4
    assert out["counts"]["positive"] >= 2
    assert out["counts"]["negative"] >= 1