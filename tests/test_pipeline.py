"""Deterministic end-to-end tests for the offline ingestion slice."""

from contextlib import redirect_stdout
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import unittest

from tweetinsights.cli import main
from tweetinsights.models import parse_event
from tweetinsights.pipeline import ingest_jsonl, summarize


class EventTests(unittest.TestCase):
    def test_normalizes_offset_time_and_deduplicates_tags_in_one_post(self):
        event = parse_event({
            "id": " p1 ", "created_at": "2026-11-10T12:00:00+02:00",
            "text": "Great #NYC #nyc #Transit", "source": "synthetic-demo"
        })
        self.assertEqual(event.created_at, "2026-11-10T10:00:00Z")
        self.assertEqual(event.hashtags, ("nyc", "transit"))
        self.assertEqual(event.sentiment, "positive")

    def test_rejects_missing_timezone_and_invalid_fields(self):
        samples = [
            {"id": "p1", "created_at": "2026-11-10T12:00:00", "text": "good"},
            {"id": "p1", "created_at": "not-a-date", "text": "good"},
            {"id": 42, "created_at": "2026-11-10T12:00:00Z", "text": "good"},
            {"id": "p1", "created_at": "2026-11-10T12:00:00Z", "text": ""},
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    parse_event(sample)

    def test_neutral_result_on_balanced_words(self):
        event = parse_event({"id": "e1", "text": "great but bad", "created_at": "2026-11-10T00:00:00Z"})
        self.assertEqual(event.sentiment, "neutral")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "events.sqlite3"

    def write(self, filename, lines):
        file = self.root / filename
        file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return file

    def test_replay_is_idempotent_and_aggregates_are_stable(self):
        src = self.write("events.jsonl", [
            json.dumps({"id": "a", "created_at": "2026-11-10T10:00:00Z", "text": "Great #NYC #NYC"}),
            json.dumps({"id": "b", "created_at": "2026-11-10T11:00:00Z", "text": "Bad #NYC #Transit"}),
            json.dumps({"id": "c", "created_at": "2026-11-11T11:00:00Z", "text": "Weather #Transit"}),
        ])
        self.assertEqual(ingest_jsonl(src, self.db), {
            "received": 3, "inserted": 3, "duplicates": 0, "rejected": 0,
        })
        self.assertEqual(ingest_jsonl(src, self.db), {
            "received": 3, "inserted": 0, "duplicates": 3, "rejected": 0,
        })
        result = summarize(self.db)
        self.assertEqual(result["total_events"], 3)
        self.assertEqual(result["sentiment"], {"positive": 1, "negative": 1, "neutral": 1})
        self.assertEqual(result["top_hashtags"], [
            {"hashtag": "nyc", "posts": 2}, {"hashtag": "transit", "posts": 2},
        ])
        self.assertEqual(result["daily_volume"], [
            {"date": "2026-11-10", "posts": 2}, {"date": "2026-11-11", "posts": 1},
        ])

    def test_invalid_records_are_quarantined_without_raw_text(self):
        src = self.write("mixed.jsonl", [
            '{"id": "a", "created_at": "2026-11-10T10:00:00Z", "text": "good #NYC"}',
            '{"id": "b", "created_at": "bad", "text": "private personal message"}',
            "{not-json",
        ])
        rejects = self.root / "rejects" / "bad.jsonl"
        result = ingest_jsonl(src, self.db, rejects)
        self.assertEqual(result, {"received": 3, "inserted": 1, "duplicates": 0, "rejected": 2})
        lines = [json.loads(s) for s in rejects.read_text().splitlines()]
        self.assertEqual([entry["line"] for entry in lines], [2, 3])
        self.assertNotIn("private personal message", rejects.read_text())
        self.assertEqual(summarize(self.db)["total_events"], 1)

    def test_cli_supports_ingest_and_summary_commands(self):
        src = self.write("input.jsonl", [
            '{"id":"one","created_at":"2026-11-10T12:00:00Z","text":"great #AI"}',
        ])
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["ingest", "--input", str(src), "--db", str(self.db)])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["inserted"], 1)
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["summary", "--db", str(self.db)])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["top_hashtags"], [
            {"hashtag": "ai", "posts": 1},
        ])


if __name__ == "__main__":
    unittest.main()
