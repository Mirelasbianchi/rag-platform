"""Plot a retrieval eval report (from retrieval_eval.py --out) as an SVG chart.

Usage: uv run python eval/plot_results.py eval/results/hashing-baseline.json docs/assets/recall.svg
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# categorical slots 1-3 of the validated reference palette (all-pairs safe for 3 series)
COLORS = {"hybrid": "#2a78d6", "keyword": "#eb6834", "vector": "#1baf7a"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def plot(report: dict, out: Path) -> None:
    results = report["results"]
    ks = sorted(int(key.split("@")[1]) for key in results[0] if key.startswith("recall@"))
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    xs = list(range(len(ks)))  # evenly spaced: k is an ordinal cut-off, not a quantity
    order = sorted(results, key=lambda r: -r[f"recall@{ks[-1]}"])
    label_y, min_gap = [], 0.06
    for r in order:
        values = [r[f"recall@{k}"] for k in ks]
        color = COLORS.get(r["mode"], MUTED)
        ax.plot(xs, values, color=color, linewidth=2, marker="o", markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=2, label=r["mode"], zorder=3)
        # push end labels apart so close series stay readable
        y = values[-1] if not label_y else min(values[-1], label_y[-1] - min_gap)
        label_y.append(y)
        mrr = next(v for key, v in r.items() if key.startswith("mrr@"))
        ax.annotate(f"{r['mode']}  {values[-1]:.0%}, MRR {mrr:.2f}", (xs[-1], values[-1]),
                    xytext=(xs[-1] + 0.12, y), textcoords="data", va="center",
                    color=INK, fontsize=10)

    ax.set_xticks(xs, [f"top {k}" for k in ks])
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0, labelsize=10)
    ax.set_xlim(-0.3, xs[-1] + 1.15)
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=MUTED)
    n = results[0]["cases"]
    fig.suptitle("Share of questions whose source article is retrieved", x=0.06, ha="left",
                 color=INK, fontsize=13, fontweight="bold")
    ax.set_title(f"{n} questions over the Consumer Defense Code (CDC), embeddings: "
                 f"{report['embedding_model']}", loc="left", color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)


if __name__ == "__main__":
    plot(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
