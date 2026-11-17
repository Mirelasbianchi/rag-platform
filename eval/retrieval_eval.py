"""Retrieval evaluation: recall@k and MRR against a running API.

Dataset format (eval/dataset.jsonl, see dataset.example.jsonl), one case per line:
    {"query": "...", "expected_document_id": 1}

Usage: uv run python eval/retrieval_eval.py --url http://localhost:8000 --k 5
"""

import argparse
import json
from pathlib import Path

import httpx


def evaluate(cases: list[dict], url: str, k: int) -> dict:
    hits, reciprocal_ranks = 0, []
    for case in cases:
        response = httpx.post(f"{url}/search", json={"query": case["query"], "k": k}, timeout=30)
        response.raise_for_status()
        ids = [hit["document_id"] for hit in response.json()]
        expected = case["expected_document_id"]
        if expected in ids:
            hits += 1
            reciprocal_ranks.append(1 / (ids.index(expected) + 1))
        else:
            reciprocal_ranks.append(0.0)
    n = len(cases)
    return {"cases": n, "k": k, f"recall@{k}": hits / n, "mrr": sum(reciprocal_ranks) / n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--dataset", default=str(Path(__file__).parent / "dataset.jsonl"))
    args = parser.parse_args()

    lines = Path(args.dataset).read_text().splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    print(json.dumps(evaluate(cases, args.url, args.k), indent=2))


if __name__ == "__main__":
    main()
