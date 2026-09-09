"""Multilingual comment sentiment analysis (Arabic + English).

Combines public token dictionaries with negation handling and an optional
AI enhancement hook. Every base rule is deterministic so the platform works
fully offline.
"""
import re

# ------------------------- Arabic dictionaries ---------------------------
_AR_POS = {
    "جيد", "ممتاز", "رائع", "جميل", "حلو", "يعجبني", "أعجبني", "احسنتم",
    "أحسنتم", "متميز", "مبدع", "ناجح", "مفيد", "رائعة", "جميلة", "ممتازة",
    "متميزة", "مبدعة", "ناجحة", "مفيدة", "شكرا", "شكراً", "يعطيك", "عافية",
    "ت", "فكرة", "ممتاع", "حبي", "احب", "احسن", "افضل", "مشكور", "حمدلله",
    "الحمد", "تسلم", "صو", "لايك", "بركة", "يحيا", "عمر", "حسن",
}

_AR_NEG = {
    "سيء", "سيئة", "رديء", "قبيح", "قبيحة", "مقرف", "غبي", "غبية", "فطاعي",
    "خسارة", "ضعيف", "ضعيفة", "مجعص", "الحقيقية", "مضيعة", "فشل", "فاشل",
    "نصب", "احتيال", "سرق", "سرقة", "لصوص", "خرب", "غش", "غشاش", "كذاب",
    "كذب", "مايك", "ميك", "يكره", "كره", "بشع", "وحش", "وقح", "مقلل",
    "تعبان", "ايح", "مزعل", "خويط",
}

# ------------------------- English dictionaries ------------------------
_EN_POS = {
    "good", "great", "awesome", "excellent", "amazing", "fantastic", "perfect",
    "wonderful", "nice", "love", "loved", "like", "liked", "best", "better",
    "cool", "beautiful", "brilliant", "impressive", " helpful", "useful",
    "recommend", "thanks", "thank", "congratulations", "congrats", "well",
    "wow", "sweet", "super", "top", "works", "working", "win", "success",
    "genius", "grateful", "appreciated", "happy", "greatly", "amazing",
    "good job", "love it", "perfectly", "impressed",
}

_EN_NEG = {
    "bad", "worst", "terrible", "awful", "horrible", "hate", "hated",
    "disgust", "disgusting", "ugly", "fake", "scam", "fraud", "broken",
    "useless", "waste", "fail", "failed", "stupid", "dumb", "cringe", "spam",
    "overpriced", "poor", "sad", "terriable", "worst", "untrusted", "garbage",
    "trash", "rubbish", "unhappy", "boring", "lame", "slow", "buggy", "error",
    "mistake", "wrong", "not", "never", "no one", "disappointed", "wasted",
}

_NEGATION = {"not", "never", "no", "dont", "don't", "doesn't", "isn't", "wasn't",
             "مش", "ما", "ليش", "مو", "لكن", "بس"}

_MARKERS = "؟؟؟!"


def looks_arabic(text: str) -> bool:
    sample = [c for c in text if c.isalpha()]
    if not sample:
        return False
    ar = sum(1 for c in sample if "\u0600" <= c <= "\u06FF")
    return ar / len(sample) >= 0.4


def _count(text: str, tokens: set) -> int:
    n = 0
    for tok in tokens:
        n += text.count(tok)
    return n


def classify_comment(text: str) -> dict:
    """Classify a single comment -> {'sentiment','score','lang','text'}."""
    text = (text or "").strip()
    if not text:
        return {"sentiment": "neutral", "score": 0.0, "lang": "unk", "text": text}

    lang = "ar" if looks_arabic(text) else "en"
    low = text.lower()

    pos = _AR_POS if lang == "ar" else _EN_POS
    neg = _AR_NEG if lang == "ar" else _EN_NEG

    pos_count = _count(low, pos)
    neg_count = _count(low, neg)

    # negation flips positive tokens to negative ("not good", "مش جيد")
    if pos_count and _count(low, _NEGATION) > 0:
        neg_count += pos_count
        pos_count = 0

    total = pos_count + neg_count
    if total == 0:
        return {"sentiment": "neutral", "score": 0.0, "lang": lang, "text": text}

    score = (pos_count - neg_count) / total
    if score > 0:
        sentiment = "positive"
    elif score < 0:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    return {"sentiment": sentiment, "score": round(score, 2), "lang": lang,
            "text": text}


def aggregate_comments(comments: list) -> dict:
    """Summarise comment list -> counts + per-comment results."""
    out = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for c in comments or []:
        res = classify_comment(c)
        counts[res["sentiment"]] += 1
        out.append({"text": c, "sentiment": res["sentiment"],
                    "score": res["score"], "lang": res["lang"]})
    total = sum(counts.values()) or 1
    return {
        "comments": out,
        "counts": counts,
        "total": sum(counts.values()),
        "good_ratio": round(counts["positive"] / total, 2),
        "bad_ratio": round((counts["negative"] + counts["neutral"]) / total, 2),
    }


def ai_classify_comments(comments: list) -> dict | None:
    """Optional AI enhancement. Returns None when no AI key is configured."""
    try:
        from app.services.ai import AIClient
        client = AIClient()
        if not client.enabled:
            return None
        labels = client.classify_comments(comments)
        if not labels or len(labels) != len(comments):
            return None
        counts = {"positive": 0, "negative": 0, "neutral": 0}
        items = []
        for text, label in zip(comments, labels):
            lbl = label if label in counts else "neutral"
            counts[lbl] += 1
            items.append({"text": text, "sentiment": lbl, "score": None, "lang": "ai"})
        total = sum(counts.values()) or 1
        return {
            "comments": items, "counts": counts, "total": sum(counts.values()),
            "good_ratio": round(counts["positive"] / total, 2),
            "bad_ratio": round((counts["negative"] + counts["neutral"]) / total, 2),
            "provider": "ai",
        }
    except Exception:
        return None