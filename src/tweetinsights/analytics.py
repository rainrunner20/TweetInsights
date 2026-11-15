"""Validate exported posts and compare two equally sized time windows."""

import csv
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HASHTAG = re.compile(r"(?<!\w)#([^\W_][\w]*)", re.UNICODE)
REQUIRED_COLUMNS = {"tweet_id", "created_at", "text", "likes", "reposts"}


@dataclass(frozen=True)
class Post:
    tweet_id: str
    created_at: datetime
    text: str
    likes: int
    reposts: int


def parse_timestamp(value: str) -> datetime:
    """Accept ISO 8601 timestamps with explicit offsets and normalize to UTC."""
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid ISO 8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Timestamp must include a timezone offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def load_posts(path: str | Path) -> list[Post]:
    """Reject bad source records rather than silently biasing trend counts."""
    posts: list[Post] = []
    ids: set[str] = set()
    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
        for line, record in enumerate(reader, start=2):
            try:
                tweet_id = (record["tweet_id"] or "").strip()
                if not tweet_id:
                    raise ValueError("tweet_id is blank")
                if tweet_id in ids:
                    raise ValueError(f"duplicate tweet_id: {tweet_id}")
                created_at = parse_timestamp(record["created_at"] or "")
                text = record["text"]
                if text is None:
                    raise ValueError("text is missing")
                likes = int(record["likes"])
                reposts = int(record["reposts"])
                if likes < 0 or reposts < 0:
                    raise ValueError("likes and reposts must be nonnegative")
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"CSV line {line}: {exc}") from exc
            posts.append(Post(tweet_id, created_at, text, likes, reposts))
            ids.add(tweet_id)
    return posts


def hashtags(text: str) -> set[str]:
    """Count each hashtag at most once per post; case variants share a tag."""
    return {match.casefold() for match in HASHTAG.findall(text)}


def analyze(posts: list[Post], start: datetime, end: datetime, top_n: int = 10) -> dict:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must be timezone-aware")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end must be timezone-aware")
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("end must be later than start")
    if not 1 <= top_n <= 100:
        raise ValueError("top_n must be between 1 and 100")
    previous_start = start - (end - start)
    current = [post for post in posts if start <= post.created_at < end]
    previous = [post for post in posts if previous_start <= post.created_at < start]

    def count(posts_in_window: list[Post]) -> Counter[str]:
        return Counter(tag for post in posts_in_window for tag in hashtags(post.text))

    curr_tags, prev_tags = count(current), count(previous)
    trends = []
    for tag, mentions in curr_tags.items():
        before = prev_tags[tag]
        delta = mentions - before
        # Positive change plus post volume rewards growing topics, not one-off spikes.
        score = round(delta * math.log1p(mentions), 3)
        trends.append({
            "hashtag": tag,
            "mentions": mentions,
            "previous_mentions": before,
            "change": delta,
            "smoothed_lift": round((mentions + 1) / (before + 1), 2),
            "trend_score": score,
        })
    trends.sort(key=lambda item: (-item["trend_score"], -item["mentions"], item["hashtag"]))

    def totals(window: list[Post]) -> dict[str, int]:
        return {
            "posts": len(window),
            "likes": sum(post.likes for post in window),
            "reposts": sum(post.reposts for post in window),
        }

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "previous_window": {"start": previous_start.isoformat(), "end": start.isoformat()},
        "current": totals(current),
        "previous": totals(previous),
        "top_hashtags": trends[:top_n],
        "source_posts": len(posts),
        "method": "post-level unique hashtags; score=(current-previous)*ln(1+current)",
    }
