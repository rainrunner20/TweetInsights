"""Validated event schema and intentionally simple sentiment baseline."""

from dataclasses import dataclass
from datetime import datetime, timezone
import re

_WORDS = re.compile(r"[a-z]+")
_HASHTAGS = re.compile(r"(?<!\w)#([a-z0-9_]{1,50})", re.IGNORECASE)
_POSITIVE = frozenset({"good", "great", "excellent", "love", "happy", "win", "improve", "safe"})
_NEGATIVE = frozenset({"bad", "poor", "awful", "hate", "sad", "lose", "fail", "unsafe"})


@dataclass(frozen=True)
class Event:
    event_id: str
    created_at: str
    text: str
    source: str
    sentiment: str
    hashtags: tuple[str, ...]


def parse_event(payload: object) -> Event:
    if not isinstance(payload, dict):
        raise ValueError("event must be a JSON object")

    event_id = payload.get("id")
    text = payload.get("text")
    timestamp = payload.get("created_at")
    source = payload.get("source", "import")

    if not isinstance(event_id, str) or not 1 <= len(event_id.strip()) <= 128:
        raise ValueError("id must be a nonempty string (max 128 characters)")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 5000:
        raise ValueError("text must be a nonempty string (max 5000 characters)")
    if not isinstance(timestamp, str):
        raise ValueError("created_at must be an ISO 8601 timestamp with a time zone")
    if not isinstance(source, str) or not 1 <= len(source.strip()) <= 50:
        raise ValueError("source must be a nonempty string (max 50 characters)")

    try:
        instant = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be an ISO 8601 timestamp") from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("created_at must include a time zone")
    utc_time = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    words = _WORDS.findall(text.casefold())
    positive = sum(word in _POSITIVE for word in words)
    negative = sum(word in _NEGATIVE for word in words)
    sentiment = "positive" if positive > negative else "negative" if negative > positive else "neutral"
    hashtags = tuple(sorted({match.casefold() for match in _HASHTAGS.findall(text)}))
    return Event(
        event_id=event_id.strip(),
        created_at=utc_time,
        text=text.strip(),
        source=source.strip(),
        sentiment=sentiment,
        hashtags=hashtags,
    )
