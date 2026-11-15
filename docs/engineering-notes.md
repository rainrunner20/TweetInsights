# Engineering notes

## Design decisions

**Replayability first.** External APIs and stream processors make debugging more difficult. The local reference pipeline keeps the input format, event time and idempotent aggregates explicit. Its tests should later run against the Kafka/Flink implementation as parity checks.

**Events have stable IDs.** Duplicate IDs are ignored even when payloads differ. This is an at-least-once ingestion strategy with idempotent writes, not a claim of distributed exactly-once execution.

**Track event time rather than ingestion time.** Timestamps must include a UTC offset. Aggregation dates are based on normalized UTC timestamps, preventing local machine timezone differences.

**Sentiment is a baseline.** A tiny transparent lexicon is appropriate for infrastructure tests but is not a validated sentiment model. It does not account for irony, slang, negation, multilingual posts, or domain shift. Report it as a lexicon baseline; accuracy has not been measured.

**Separate invalid data from valid data.** Rejected records are counted and can be logged by line number and validation reason. The raw post text is deliberately omitted from the rejects output to reduce unnecessary reproduction of personal information.

## Operational limitations

- SQLite is single-host storage and is not the final streaming warehouse.
- The MVP does not connect to Kafka, Flink, Elasticsearch, Kibana or X; the LinkedIn stack claims are not yet supported by executable code.
- A crash mid-batch may lose some uncommitted writes, but replay is safe because previously committed IDs remain unique.
- There is no access control or retention policy for the local database. Do not run it as a multi-user production system.
- Generated analytics describe the records ingested, not public opinion or representative population-level outcomes.

## Verification checklist

1. `python -m unittest discover -s tests -v` passes.
2. The synthetic sample inserts four records once and zero new records on replay.
3. The CLI summary reports two positive, one negative, one neutral post and three posts with #nyc.
4. Malformed lines create a counted reject record without storing their original text in the reject file.
5. GitHub Actions passes on the pull request; preserve the feature branch after review.
