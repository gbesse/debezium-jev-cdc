"""Pinned Jev choice call for changed CDC text."""
import json
import math
from urllib.request import Request, urlopen

API_URL = "https://api.typesafe.ai/v1/systemone"

class DecisionError(Exception):
    pass

def decide(text, policy, key, *, opener=urlopen):
    if not isinstance(text, str) or not text.strip() or len(text) > 16000:
        raise DecisionError("invalid text")
    if not key:
        raise DecisionError("missing key")
    question = policy["question"]
    body = {"model": policy["model"], "state": {"text": text}, "questions": {
        question: {"type": "choice", "instructions": policy["instructions"], "criteria": policy["criteria"]}}}
    request = Request(API_URL, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with opener(request, timeout=20) as response:
            answer = json.load(response)
    except Exception as exc:
        raise DecisionError("Jev request failed") from exc
    if answer.get("model") != policy["model"]:
        raise DecisionError("model mismatch")
    selected = answer.get("answers", {}).get(question, {})
    choice = selected.get("choice")
    probabilities = selected.get("probabilities", {})
    probability = probabilities.get(choice) if isinstance(probabilities, dict) else None
    if (choice not in policy["criteria"] or isinstance(probability, bool)
            or not isinstance(probability, (int, float)) or not math.isfinite(probability)
            or not 0 <= probability <= 1):
        raise DecisionError("invalid answer")
    return {"choice": choice, "probability": probability,
            "outcome": choice if choice != "other" and probability >= policy["threshold"] else "review"}
