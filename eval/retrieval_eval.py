"""Retrieval evaluation: recall@k, MRR and latency against a running API.

Dataset format (eval/dataset.jsonl), one case per line. Each case names the document it
should retrieve, by source (preferred) or by id:
    {"query": "...", "expected_source": "cdc:art-49"}
    {"query": "...", "expected_document_id": 1}

Usage:
    uv run python eval/retrieval_eval.py --url http://localhost:8000
    uv run python eval/retrieval_eval.py --modes hybrid --ks 1 5 --out eval/results/run.json
"""

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

EVAL_DIR = Path(__file__).parent


def _key(case: dict) -> tuple[str, object]:
    if "expected_source" in case:
        return "source", case["expected_source"]
    return "document_id", case["expected_document_id"]


def first_rank(hits: list[dict], field: str, expected) -> int | None:
    """1-based rank of the first chunk from the expected document, or None."""
    for rank, hit in enumerate(hits, start=1):
        if hit[field] == expected:
            return rank
    return None


def evaluate(cases: list[dict], url: str, mode: str, ks: list[int]) -> dict:
    depth = max(ks)
    ranks, latencies, misses = [], [], []
    with httpx.Client(base_url=url, timeout=60) as client:
        for case in cases:
            start = time.perf_counter()
            response = client.post("/search", json={"query": case["query"], "k": depth, "mode": mode})
            latencies.append((time.perf_counter() - start) * 1000)
            response.raise_for_status()
            field, expected = _key(case)
            rank = first_rank(response.json(), field, expected)
            ranks.append(rank)
            if rank is None or rank > 1:
                misses.append({"query": case["query"], "expected": expected, "rank": rank})

    n = len(cases)
    metrics = {f"recall@{k}": sum(r is not None and r <= k for r in ranks) / n for k in ks}
    metrics[f"mrr@{depth}"] = sum(1 / r for r in ranks if r) / n
    latencies.sort()
    return {
        "mode": mode,
        "cases": n,
        **{name: round(value, 4) for name, value in metrics.items()},
        "latency_ms_p50": round(statistics.median(latencies), 1),
        "latency_ms_p95": round(latencies[int(0.95 * (n - 1))], 1),
        "not_at_rank_1": misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--dataset", default=str(EVAL_DIR / "dataset.jsonl"))
    parser.add_argument("--modes", nargs="+", default=["vector", "keyword", "hybrid"])
    parser.add_argument("--ks", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--out", help="write the full report as JSON to this path")
    args = parser.parse_args()

    lines = Path(args.dataset).read_text().splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    health = httpx.get(f"{args.url}/ready", timeout=10).json()

    results = [evaluate(cases, args.url, mode, args.ks) for mode in args.modes]
    report = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "embedding_model": health.get("embedding_model"),
        "dataset": Path(args.dataset).name,
        "results": results,
    }

    header = ["mode", *[f"recall@{k}" for k in args.ks], f"mrr@{max(args.ks)}", "p50 ms"]
    print(" | ".join(f"{h:>10}" for h in header))
    for r in results:
        row = [r["mode"], *[r[f"recall@{k}"] for k in args.ks], r[f"mrr@{max(args.ks)}"],
               r["latency_ms_p50"]]
        print(" | ".join(f"{v:>10.3f}" if isinstance(v, float) else f"{v:>10}" for v in row))

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
