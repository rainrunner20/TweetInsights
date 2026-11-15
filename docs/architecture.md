# Architecture and tradeoffs

## Scope of this milestone

Input: exported CSV with fixed columns. Processing: strict validation, UTC normalization,
post-level hashtag extraction, comparison against an immediately preceding window of
equal duration. Outputs: deterministic JSON and an optional self-contained HTML dashboard.
No external credentials or internet connection are necessary.

## Why batch processing first?

A trustworthy baseline is easier to verify without a streaming stack. The batch
implementation gives us a reference result that future Kafka/Flink implementations
must match on replayed input. It also makes test failures easier to isolate.

## Decisions

- **No silent row skipping**: malformed rows and duplicate IDs fail with the CSV line number.
  A future ingestion layer can quarantine invalid rows and report rejection counts.
- **UTC-only comparisons**: offset timestamps are normalized to UTC. This avoids daylight-
  saving ambiguities and ensures fixed-length windows.
- **One hashtag mention per post**: repeating a tag does not artificially inflate volume.
- **Simple, inspectable trend score**: `(current - previous) * ln(1 + current)` ranks
  growing tags, factoring in current conversation volume. This is a descriptive heuristic,
  not a statistical significance test or a predictor of future popularity.
- **No inferred sentiment**: a hashtag trend does not imply users support its content.
- **No raw post text in reports**: only aggregate counts are exported to JSON/HTML.

## Known gaps and next steps

1. Introduce a schema-mapped connector for lawful, permitted platform exports.
2. Build ingestion with quarantine, audit counts, and idempotent event handling.
3. Benchmark trend ranking against manually annotated historical windows.
4. Add a stream processor and reconcile outputs against this batch reference.
5. Add deployment and observability after defining realistic costs and privacy limits.

All sample data in `data/demo_posts.csv` is synthetic. The project does not currently
connect to the live X/Twitter API, Kafka, Flink, a social firehose, or a hosted database.
