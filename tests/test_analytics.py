"""Regression tests for ingestion and trend calculations, with no internet required."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tweetinsights.analytics import Post, analyze, hashtags, load_posts, parse_timestamp
from tweetinsights.report import render_dashboard


class CsvTests(unittest.TestCase):
    def load(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "posts.csv"
            path.write_text(text, encoding="utf-8")
            return load_posts(path)

    def test_csv_parses_offset_timestamps(self):
        posts = self.load("tweet_id,created_at,text,likes,reposts\na,2026-11-01T02:00:00+02:00,#Bike,5,2\n")
        self.assertEqual(posts[0].created_at, datetime(2026, 11, 1, tzinfo=timezone.utc))
        self.assertEqual(posts[0].likes, 5)

    def test_duplicate_ids_fail_instead_of_distorting_counts(self):
        with self.assertRaisesRegex(ValueError, "line 3.*duplicate"):
            self.load("tweet_id,created_at,text,likes,reposts\na,2026-11-01T00:00:00Z,first,0,0\na,2026-11-02T00:00:00Z,second,0,0\n")

    def test_rejects_missing_columns_and_negative_engagement(self):
        with self.assertRaisesRegex(ValueError, "Missing CSV columns"):
            self.load("tweet_id,text\n1,hi\n")
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            self.load("tweet_id,created_at,text,likes,reposts\na,2026-11-01T00:00:00Z,hi,-1,0\n")

    def test_timestamps_require_explicit_timezone(self):
        with self.assertRaisesRegex(ValueError, "timezone offset"):
            parse_timestamp("2026-11-01T00:00:00")


class TrendTests(unittest.TestCase):
    def p(self, uid: str, date: str, text: str, likes=1, reposts=0):
        return Post(uid, parse_timestamp(date), text, likes, reposts)

    def test_compare_equal_windows_end_exclusive_and_unique_hashtags(self):
        posts = [
            self.p("1", "2026-10-25T00:00:00Z", "#Bike #Bike"),
            self.p("2", "2026-10-31T23:59:59Z", "#BIKE #rain"),
            self.p("3", "2026-11-01T00:00:00Z", "#bike #BIKE #ai", 5, 2),
            self.p("4", "2026-11-03T00:00:00Z", "#bike #ai", 4, 1),
            self.p("5", "2026-11-07T23:59:59Z", "#ai", 3, 1),
            self.p("6", "2026-11-08T00:00:00Z", "#ai"),
        ]
        result = analyze(posts, parse_timestamp("2026-11-01T00:00:00Z"), parse_timestamp("2026-11-08T00:00:00Z"))
        self.assertEqual(result["current"], {"posts": 3, "likes": 12, "reposts": 4})
        self.assertEqual(result["previous"]["posts"], 2)
        by_tag = {entry["hashtag"]: entry for entry in result["top_hashtags"]}
        self.assertEqual(by_tag["bike"]["mentions"], 2)
        self.assertEqual(by_tag["bike"]["previous_mentions"], 2)
        self.assertEqual(by_tag["ai"]["mentions"], 3)
        self.assertEqual(result["top_hashtags"][0]["hashtag"], "ai")

    def test_rejects_invalid_windows_and_limits(self):
        day = parse_timestamp("2026-11-01T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "later"):
            analyze([], day, day)
        with self.assertRaisesRegex(ValueError, "top_n"):
            analyze([], day, day.replace(day=2), 0)

    def test_html_escapes_unsafe_tag_names(self):
        data = analyze([self.p("1", "2026-11-01T00:00:00Z", "#Safe")], parse_timestamp("2026-11-01T00:00:00Z"), parse_timestamp("2026-11-08T00:00:00Z"))
        data["top_hashtags"][0]["hashtag"] = '<script>alert(1)</script>'
        html = render_dashboard(data, sample_data=True)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("SYNTHETIC SAMPLE DATA", html)

    def test_casefold_and_avoid_matching_email_ish_words(self):
        self.assertEqual(hashtags("#Transit #TRANSIT test#bad #AI_projects"), {"transit", "ai_projects"})


if __name__ == "__main__":
    unittest.main()
