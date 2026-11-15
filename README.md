# TweetInsights

**TweetInsights** turns exported social posts into an explainable topic-trend report. The
current milestone is a small, working batch analytics app that can run locally with no
API keys, services, or network calls.

## Demo

The included CSV contains **synthetic data** for a fictional conversation about urban
mobility and data visualization. It does not claim to represent live X/Twitter trends.
The generated dark-mode HTML report is completely self-contained and can be opened in
a browser without a server.

### Quick start (PowerShell, Python 3.11+)

```powershell
git clone https://github.com/rainrunner20/TweetInsights.git
cd TweetInsights
py -m pip install -e .
py -m tweetinsights --input data/demo_posts.csv --start 2026-11-01T00:00:00Z --end 2026-11-08T00:00:00Z --output reports/demo.json --html reports/demo.html --sample-data
Start-Process reports/demo.html
py -m unittest discover -s tests -v
```

You can also run `tweetinsights` directly after installation.

### CSV schema

| Column | Meaning | Example |
| --- | --- | --- |
| `tweet_id` | Unique identifier within the input file | `p01` |
| `created_at` | ISO 8601 timestamp **with timezone** | `2026-11-01T09:00:00Z` |
| `text` | Post text; quoted CSV if it contains commas | `#Transit is changing` |
| `likes` | Nonnegative integer | `14` |
| `reposts` | Nonnegative integer | `2` |

Invalid records fail with a line number. Duplicate IDs fail instead of inflating trends.
No raw post text appears in the generated reports.

### How it works

1. Validate each input post and normalize timestamps to UTC.
2. Select a time window and the preceding window of the same duration.
3. Extract case-insensitive hashtags, counting each hashtag once per post.
4. Rank current hashtags by `(current_mentions - previous_mentions) * ln(1 + current_mentions)`.
5. Export aggregate totals and scores to JSON and optionally visualize them in HTML.

A score measures observed change, not sentiment, truthfulness, statistical significance,
or future popularity. See [architecture and tradeoffs](docs/architecture.md).

### Validation

GitHub Actions runs all unit tests on Python 3.11, 3.12, and 3.13 and smoke-tests
report generation. No test calls external APIs.

## Current status

- [x] Reproducible CSV ingestion and UTC-based analysis
- [x] Transparent hashtag trend scoring
- [x] Offline JSON and standalone visual dashboard
- [x] Regression tests and CI
- [ ] Live platform ingestion or Kafka/Flink streaming
- [ ] Statistical evaluation on real-world labeled data
- [ ] Production deployment, authentication, monitoring

This is a working analytics baseline, **not** a deployed social listening service.
