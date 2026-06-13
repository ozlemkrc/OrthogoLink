"""
Generate the evaluation figures for the thesis from a benchmark results JSON.

This reads the JSON produced by ``benchmark.py`` (use the ``--compare`` run, which
contains both the ``baseline`` and ``rerank`` modes) and writes three PNGs:

    eval_threshold_sweep.png  precision / recall / F1 / accuracy vs. similarity cutoff
    eval_pr_curve.png         precision-recall curve across the swept cutoffs
    eval_separation.png       per-proposal weakest-true-overlap vs. strongest-false-match

It deliberately does NO benchmarking itself; it only plots numbers already in the
JSON, so it is fast and needs no model.

Usage (from the ``backend`` directory):

    pip install matplotlib
    python -m eval.make_figures                         # reads eval/bench_results.json
    python -m eval.make_figures --json eval/bench_results.json --mode baseline
    python -m eval.make_figures --outdir ../OrthogoLink__.../Imgs   # write straight into the thesis

By default it plots the ``baseline`` (bi-encoder) mode, which is the operating
configuration the thesis headlines; pass ``--mode rerank`` for the cross-encoder run.
"""
import argparse
import json
import os
import sys


def _load_mode(path: str, mode: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # A --compare run nests modes under "baseline"/"rerank"; a plain run is flat.
    block = data.get(mode, data)
    if "sweep" not in block:
        sys.exit(
            f"Could not find a '{mode}' block with a 'sweep' in {path}. "
            "Run 'python -m eval.benchmark --compare --json eval/bench_results.json' first."
        )
    return block, data


def plot_threshold_sweep(block: dict, outdir: str) -> str:
    import matplotlib.pyplot as plt

    sweep = sorted(block["sweep"], key=lambda r: r["threshold"])
    x = [r["threshold"] for r in sweep]
    best_t = block.get("best_threshold")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key, label, marker in [
        ("precision", "Precision", "o"),
        ("recall", "Recall", "s"),
        ("f1", r"$F_1$", "^"),
        ("accuracy", "Accuracy", "d"),
    ]:
        ax.plot(x, [r[key] for r in sweep], marker=marker, label=label, linewidth=1.8)

    if best_t is not None:
        ax.axvline(best_t, color="0.4", linestyle="--", linewidth=1.2)
        ax.text(best_t, 0.02, f" best $F_1$ cutoff = {best_t:g}",
                rotation=90, va="bottom", ha="right", color="0.3", fontsize=9)

    ax.set_xlabel("Similarity cutoff $\\tau$")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(min(x), max(x))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower center", ncol=4, frameon=False)
    fig.tight_layout()

    path = os.path.join(outdir, "eval_threshold_sweep.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_pr_curve(block: dict, outdir: str) -> str:
    import matplotlib.pyplot as plt

    sweep = sorted(block["sweep"], key=lambda r: r["recall"])
    recall = [r["recall"] for r in sweep]
    precision = [r["precision"] for r in sweep]

    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot(recall, precision, marker="o", linewidth=1.8, color="#0277BD")
    for r in block["sweep"]:
        ax.annotate(f"{r['threshold']:g}", (r["recall"], r["precision"]),
                    textcoords="offset points", xytext=(4, 4), fontsize=8, color="0.4")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.set_title("Precision-recall across swept cutoffs", fontsize=11)
    fig.tight_layout()

    path = os.path.join(outdir, "eval_pr_curve.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_separation(block: dict, full: dict, outdir: str) -> str:
    import matplotlib.pyplot as plt

    cutoff = block.get("best_threshold") or full.get("configured_threshold", 0.75)

    rows = []  # (name, weakest_true, strongest_false)
    for q in block["per_query"]:
        sims = q["similarities"]
        expected = set(q["expected_overlap"])
        true_scores = [sims[c] for c in expected if c in sims]
        false_scores = [v for c, v in sims.items() if c not in expected]
        rows.append((
            q["query"],
            min(true_scores) if true_scores else None,
            max(false_scores) if false_scores else None,
        ))

    # Order proposals by their weakest true overlap so the separation reads top-down.
    rows.sort(key=lambda r: (r[1] is None, r[1] if r[1] is not None else 1.0))
    names = [r[0] for r in rows]
    y = range(len(rows))

    fig, ax = plt.subplots(figsize=(8, 0.45 * len(rows) + 1.5))
    ax.axvline(cutoff, color="0.4", linestyle="--", linewidth=1.3,
               label=f"operating cutoff = {cutoff:g}")
    for i, (_, true_min, false_max) in zip(y, rows):
        if true_min is not None:
            ax.scatter(true_min, i, color="#2E7D32", s=70, zorder=3,
                       label="weakest true overlap" if i == 0 else None)
        if false_max is not None:
            ax.scatter(false_max, i, color="#C62828", marker="x", s=70, zorder=3,
                       label="strongest false match" if i == 0 else None)

    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Course-level similarity")
    ax.set_xlim(0, 1.0)
    ax.grid(True, axis="x", alpha=0.3)
    # Markers all sit at similarity > 0.4, so the lower-left corner is empty and
    # the legend can live there without covering any data point.
    ax.legend(loc="lower left", fontsize=9, frameon=True)
    fig.tight_layout()

    path = os.path.join(outdir, "eval_separation.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot evaluation figures from benchmark JSON")
    parser.add_argument("--json", default=os.path.join("eval", "bench_results.json"),
                        help="Path to benchmark results JSON (default: eval/bench_results.json)")
    parser.add_argument("--mode", choices=["baseline", "rerank"], default="baseline",
                        help="Which mode to plot from a --compare run (default: baseline)")
    parser.add_argument("--outdir", default="eval",
                        help="Directory to write the PNGs into (default: eval)")
    args = parser.parse_args()

    block, full = _load_mode(args.json, args.mode)
    os.makedirs(args.outdir, exist_ok=True)

    written = [
        plot_threshold_sweep(block, args.outdir),
        plot_pr_curve(block, args.outdir),
        plot_separation(block, full, args.outdir),
    ]
    print("Wrote:")
    for p in written:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
