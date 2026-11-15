"""Command-line entrypoint for reproducible, offline trend analysis."""

import argparse
import json
import sys

from .pipeline import ingest_jsonl, summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TweetInsights: replayable post analytics")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Ingest newline-delimited JSON events")
    ingest.add_argument("--input", required=True, help="Path to a JSONL event file")
    ingest.add_argument("--db", default="data/tweetinsights.sqlite3", help="SQLite storage path")
    ingest.add_argument("--rejects", help="Write rejected line numbers and reasons to this JSONL file")
    ingest.add_argument("--fail-on-rejects", action="store_true", help="Exit nonzero when records fail validation")

    summary = commands.add_parser("summary", help="Report sentiment and hashtag volumes")
    summary.add_argument("--db", default="data/tweetinsights.sqlite3", help="SQLite storage path")
    summary.add_argument("--top", type=int, default=10, help="Number of hashtags to return (1–100)")

    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            result = ingest_jsonl(args.input, args.db, args.rejects)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2 if args.fail_on_rejects and result["rejected"] else 0

        result = summarize(args.db, args.top)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"tweetinsights: {exc}", file=sys.stderr)
        return 1
