import io
import json
import sqlite3
import unittest
from cdc import run

with open("examples/policy.json", encoding="utf-8") as source:
    POLICY = json.load(source)

class CdcTests(unittest.TestCase):
    def database(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE decisions(source_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)")
        return db

    def test_change_only_and_delete(self):
        with open("examples/changes.jsonl", encoding="utf-8") as source:
            events = source.read()
        db, output, review, calls = self.database(), io.StringIO(), io.StringIO(), []
        def evaluate(text, _policy):
            calls.append(text)
            return {"choice": "yes", "probability": 0.96, "outcome": "yes"}
        self.assertEqual(run(io.StringIO(events), output, review, db, POLICY, evaluate), (2, 0))
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([row["op"] for row in rows], ["upsert", "delete"])
        self.assertEqual(calls, ["The refund never arrived"])
        self.assertNotIn("refund", output.getvalue())
        self.assertEqual(db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_bad_row_is_reviewed_without_stopping_next_row(self):
        db, output, review = self.database(), io.StringIO(), io.StringIO()
        with open("examples/changes.jsonl", encoding="utf-8") as source:
            valid = source.readline()
        result = run(io.StringIO('broken\n' + valid), output, review, db, POLICY,
                     lambda *_: {"choice": "no", "probability": .97, "outcome": "no"})
        self.assertEqual(result, (1, 1))
        self.assertEqual(json.loads(review.getvalue())["line"], 1)
