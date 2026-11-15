"""Export deterministic JSON and an optional shareable HTML report."""

import argparse
import json
from pathlib import Path

from tweetinsights.analytics import analyze, load_posts, parse_timestamp
from tweetinsights.report import render_dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare hashtag trends in exported social posts")
    parser.add_argument("--input", type=Path, required=True, help="CSV with tweet_id,created_at,text,likes,reposts")
    parser.add_argument("--start", required=True, help="UTC window start, e.g. 2026-11-01T00:00:00Z")
    parser.add_argument("--end", required=True, help="Exclusive UTC window end")
    parser.add_argument("--output", type=Path, required=True, help="Path to JSON report")
    parser.add_argument("--html", type=Path, help="Optional standalone HTML dashboard")
    parser.add_argument("--top", type=int, default=10, help="Maximum number of topics")
    parser.add_argument("--sample-data", action="store_true", help="Mark generated HTML as synthetic demo data")
    args = parser.parse_args(argv)

    try:
        result = analyze(load_posts(args.input), parse_timestamp(args.start), parse_timestamp(args.end), args.top)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote JSON report: {args.output}")
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_dashboard(result, sample_data=args.sample_data), encoding="utf-8")
        print(f"Wrote HTML dashboard: {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
