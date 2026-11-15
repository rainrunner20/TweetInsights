"""Streaming JSONL ingestion and replay-safe SQLite analytics."""

from contextlib import ExitStack, closing
import json
from pathlib import Path
import sqlite3

from .models import Event, parse_event


def _open_database(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            body TEXT NOT NULL,
            source TEXT NOT NULL,
            sentiment TEXT NOT NULL CHECK(sentiment IN ('positive', 'neutral', 'negative'))
        );
        CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
        CREATE TABLE IF NOT EXISTS event_hashtags (
            event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
            hashtag TEXT NOT NULL,
            PRIMARY KEY (event_id, hashtag)
        );
        CREATE INDEX IF NOT EXISTS idx_event_hashtags_hashtag ON event_hashtags(hashtag);
        """
    )
    return conn


def ingest_jsonl(
    input_path: str | Path,
    db_path: str | Path,
    rejects_path: str | Path | None = None,
) -> dict[str, int]:
    """Process one line at a time; replaying the same IDs never doubles counts."""
    stats = {"received": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    with ExitStack() as stack:
        source = stack.enter_context(Path(input_path).open(encoding="utf-8"))
        database = stack.enter_context(closing(_open_database(db_path)))
        rejects = None
        if rejects_path is not None:
            target = Path(rejects_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            rejects = stack.enter_context(target.open("w", encoding="utf-8"))

        try:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                stats["received"] += 1
                try:
                    event = parse_event(json.loads(line))
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    stats["rejected"] += 1
                    if rejects is not None:
                        # Store line numbers and validation failures, not private raw text.
                        rejects.write(json.dumps({"line": line_number, "error": str(exc)}) + "\n")
                    continue

                result = database.execute(
                    """INSERT OR IGNORE INTO events(event_id, created_at, body, source, sentiment)
                       VALUES (?, ?, ?, ?, ?)""",
                    (event.event_id, event.created_at, event.text, event.source, event.sentiment),
                )
                if result.rowcount == 0:
                    stats["duplicates"] += 1
                else:
                    database.executemany(
                        "INSERT INTO event_hashtags(event_id, hashtag) VALUES (?, ?)",
                        ((event.event_id, tag) for tag in event.hashtags),
                    )
                    stats["inserted"] += 1

                # Bounded transaction size; a failed run can safely replay committed IDs.
                if stats["received"] % 500 == 0:
                    database.commit()
            database.commit()
        except Exception:
            database.rollback()
            raise

    return stats


def summarize(db_path: str | Path, top_n: int = 10) -> dict:
    if not 1 <= top_n <= 100:
        raise ValueError("top_n must be between 1 and 100")

    with closing(_open_database(db_path)) as database:
        total, first, last = database.execute(
            "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM events"
        ).fetchone()
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for sentiment, count in database.execute(
            "SELECT sentiment, COUNT(*) FROM events GROUP BY sentiment"
        ):
            sentiment_counts[sentiment] = count

        tags = [
            {"hashtag": hashtag, "posts": count}
            for hashtag, count in database.execute(
                """SELECT hashtag, COUNT(*) FROM event_hashtags
                   GROUP BY hashtag ORDER BY COUNT(*) DESC, hashtag ASC LIMIT ?""",
                (top_n,),
            )
        ]
        daily = [
            {"date": day, "posts": count}
            for day, count in database.execute(
                """SELECT SUBSTR(created_at, 1, 10), COUNT(*) FROM events
                   GROUP BY SUBSTR(created_at, 1, 10) ORDER BY 1"""
            )
        ]
    return {
        "total_events": total,
        "first_event_at": first,
        "last_event_at": last,
        "sentiment": sentiment_counts,
        "top_hashtags": tags,
        "daily_volume": daily,
        "classification": "lexicon-baseline-not-ML",
    }
