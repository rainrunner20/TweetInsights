# TweetInsights

A replayable, **offline-first** pipeline for analyzing posts over time. This repository originally contained only a short README; the first implemented milestone provides a working Python ingestion engine, SQL-backed aggregates, a command-line interface, and regression tests.

> **Implementation status:** local JSONL replay + SQLite analytics. This does **not yet** use the live Twitter/X API, Apache Kafka, Flink, Elasticsearch, or Kibana. Those are planned integrations, not delivered features or measured throughput claims.

## What it does

- Streams newline-delimited JSON records without loading the entire file into memory.
- Validates IDs, text, source provenance and timezone-aware event timestamps.
- Normalizes event time to UTC, extracts hashtags, and assigns an explainable **lexicon baseline** sentiment label (not an ML classifier).
- Inserts events idempotently using their IDs, so restarting/replaying data does not double-count them.
- Quarantines malformed records by line number and error message, without copying their raw text into the rejection log.
- Reports event volume by day, positive/neutral/negative counts and the most frequent hashtags in a stable JSON format.

## Quickstart (PowerShell, Python 3.11+)

```powershell
git clone https://github.com/rainrunner20/TweetInsights.git
cd TweetInsights
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m tweetinsights ingest --input examples/synthetic-posts.jsonl --db data/tweetinsights.sqlite3 --rejects rejected-events.jsonl
python -m tweetinsights summary --db data/tweetinsights.sqlite3 --top 10
python -m unittest discover -s tests -v
```

The sample file contains **four synthetic posts, not real social-media activity**. After first ingestion the summary should contain 4 events, with 2 positive, 1 negative and 1 neutral sentiment labels. Re-run ingest and the four IDs will be counted as duplicates rather than inserted again.

## Data contract

Each JSONL line must have:

```json
{"id":"demo-001","created_at":"2026-11-10T10:00:00Z","text":"Great #NYC transit improvements","source":"synthetic-demo"}
```

- `id`: unique nonempty string, maximum 128 characters.
- `created_at`: ISO 8601 timestamp **including a timezone**.
- `text`: nonempty string, maximum 5,000 characters.
- `source`: provenance label, max 50 characters (defaults to `import`).

Storage: `events` and `event_hashtags` SQLite tables with primary keys, a foreign key constraint, and indexes. Retained text is stored locally; do not ingest private or copyrighted bulk datasets without proper permissions. Never commit generated databases. Duplicate IDs retain the first ingested event.

## Architecture

```text
JSONL file (synthetic / permitted export)
  -> schema + event-time validation
  -> baseline sentiment and hashtag extraction
  -> idempotent SQLite event store
  -> daily volume, sentiment and hashtag reports
```

## Engineering roadmap

1. **Completed in this milestone:** deterministic offline ingestion, idempotency, quarantine, CLI, tests, CI.
2. **Planned:** modular connector interface and a Kafka producer/consumer pair with reliable offsets and replay tests.
3. **Planned:** Flink event-time windows, watermarks and late-event test cases, feeding Elasticsearch.
4. **Planned:** Kibana dashboards, local Docker Compose demo, backpressure benchmarks, metrics, security and deployment documentation.
5. **Planned:** validated sentiment models and systematic evaluation against labeled data (the current dictionary approach is only a baseline).

Do not report multi-terabyte throughput or three-node Kafka deployment without actually running and documenting those benchmarks. See `docs/engineering-notes.md` for assumptions and limitations.
