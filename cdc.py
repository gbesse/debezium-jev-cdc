"""Change-only Jev decisions from Debezium JSON envelopes to sidecar JSONL."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
from decision import decide


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def normalized(event):
    if event is None:
        return None
    if not isinstance(event, dict):
        raise ValueError("object required")
    payload = event.get("payload", event)
    if payload is None:
        return None
    if not isinstance(payload, dict) or payload.get("op") not in ("c", "u", "r", "d"):
        raise ValueError("unsupported envelope")
    source = payload.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("table"), str):
        raise ValueError("source table required")
    row = payload.get("before") if payload["op"] == "d" else payload.get("after")
    if not isinstance(row, dict):
        raise ValueError("row required")
    return payload, source, row


def process(event, db, policy, evaluate):
    item = normalized(event)
    if item is None:
        return None
    payload, source, row = item
    pk = row.get(policy["primary_key"])
    if pk is None or isinstance(pk, (dict, list, bool)):
        raise ValueError("invalid primary key")
    identity = [source.get("db"), source.get("schema"), source["table"], pk]
    key = json.dumps(identity, separators=(",", ":"), ensure_ascii=False)
    source_id = {"db": identity[0], "schema": identity[1], "table": identity[2], "pk": pk}
    if payload["op"] == "d":
        db.execute("DELETE FROM decisions WHERE source_key=?", (key,))
        return {"op": "delete", "source": source_id, "policy_version": policy["version"],
                "event_id": digest(key + ":delete:" + policy["version"])}
    value = row.get(policy["text_field"])
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonempty text required")
    text_hash = digest(value)
    fingerprint = digest(policy["version"] + ":" + text_hash)
    previous = db.execute("SELECT fingerprint FROM decisions WHERE source_key=?", (key,)).fetchone()
    if previous and previous[0] == fingerprint:
        return None
    result = evaluate(value, policy)
    if result["choice"] not in policy["criteria"] or result["outcome"] not in (*policy["criteria"], "review"):
        raise ValueError("invalid decision")
    probability = result["probability"]
    if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("invalid probability")
    db.execute("INSERT INTO decisions(source_key,fingerprint) VALUES(?,?) "
               "ON CONFLICT(source_key) DO UPDATE SET fingerprint=excluded.fingerprint", (key, fingerprint))
    return {"op": "upsert", "source": source_id, "policy_version": policy["version"],
            "choice": result["choice"], "probability": probability, "outcome": result["outcome"],
            "text_sha256": text_hash, "event_id": digest(key + ":" + fingerprint)}


def run(lines, output, review, db, policy, evaluate):
    ok = bad = 0
    for number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
            with db:
                result = process(event, db, policy, evaluate)
                if result is not None:
                    output.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
                    output.flush()
                    ok += 1
        except (ValueError, KeyError, TypeError) as exc:
            review.write(json.dumps({"line": number, "raw": line.rstrip("\n"),
                                     "error_type": type(exc).__name__}, ensure_ascii=False) + "\n")
            bad += 1
    review.flush()
    return ok, bad


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--policy", default="examples/policy.json")
    parser.add_argument("--state", default=".local/state.sqlite")
    parser.add_argument("--review", default=".local/review.jsonl")
    parser.add_argument("--fixtures")
    args = parser.parse_args()
    os.umask(0o077)
    paths = [Path(p).resolve() for p in (args.input, args.policy, args.state, args.review)]
    if len(set(paths)) != len(paths):
        parser.error("input, policy, state and review paths must differ")
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    if not isinstance(policy.get("threshold"), (int, float)) or isinstance(policy["threshold"], bool) or not 0 < policy["threshold"] <= 1:
        parser.error("invalid threshold")
    if args.fixtures:
        fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
        def evaluate(text, _policy):
            return fixtures[text]
    else:
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            parser.error("TYPESAFE_API_KEY required without --fixtures")
        def evaluate(text, current_policy):
            return decide(text, current_policy, key)
    Path(args.state).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    Path(args.review).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sqlite3.connect(args.state) as db:
        db.execute("CREATE TABLE IF NOT EXISTS decisions(source_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)")
        os.chmod(args.state, 0o600)
        with open(args.input, encoding="utf-8") as source, open(args.review, "a", encoding="utf-8") as review:
            os.chmod(args.review, 0o600)
            ok, bad = run(source, sys.stdout, review, db, policy, evaluate)
    print(f"upserts_or_deletes={ok} review={bad}", file=sys.stderr)
    if bad:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
