"""
Evaluation harness for overlap-detection quality.

Builds a FAISS index from the labeled ``CATALOG`` (using the *real* embedding
model configured in ``settings.MODEL_NAME``), runs every proposed-course query
through the production ``compare_syllabus`` pipeline, and measures how well the
course-level overlap decision matches the human-labeled ground truth in
``dataset.py``.

The key output is a **threshold sweep**: precision, recall, and F1 of the
binary "is this catalog course an overlap?" decision at each candidate cutoff.
This turns "we chose 0.70" into an empirical claim — e.g. "0.70 maximizes F1 on
our benchmark" — and shows the precision/recall trade-off a reviewer will ask
about.

Run from the ``backend`` directory (so ``app`` is importable):

    python -m eval.benchmark
    python -m eval.benchmark --json results.json   # also dump machine-readable

Requires the real dependencies (sentence-transformers, faiss-cpu) and will
download the model on first run (~90-400MB depending on MODEL_NAME). Inside the
project this is already available in the backend Docker image:

    docker compose run --rm backend python -m eval.benchmark
"""
import argparse
import json
import sys
from dataclasses import dataclass

import numpy as np

from app.services.embedding_service import embedding_service
from app.services.pdf_service import split_into_sections
from app.services.comparison_service import compare_syllabus
from app.core.config import get_settings
from eval.dataset import CATALOG, QUERIES, CatalogCourse

# Candidate cutoffs to sweep. Includes the configured default for reference.
SWEEP_THRESHOLDS = [round(0.40 + 0.05 * i, 2) for i in range(11)]  # 0.40 .. 0.90

# Low cutoff used when collecting raw candidate similarities so weak matches are
# not pruned before we sweep thresholds ourselves.
COLLECTION_THRESHOLD = 0.30


@dataclass
class Metrics:
    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / total if total else 0.0


def build_catalog_index(catalog: list[CatalogCourse]) -> None:
    """Embed every catalog course's sections and build the FAISS index, mirroring
    the metadata layout that ``course_service`` produces in production."""
    embedding_service.load_model()

    all_embeddings: list[np.ndarray] = []
    metadata: list[dict] = []
    for course_id, course in enumerate(catalog, start=1):
        sections = split_into_sections(course.description)
        texts = [f"{s['heading']}: {s['content']}" for s in sections]
        embeddings = embedding_service.encode(texts)
        all_embeddings.append(embeddings)
        for section in sections:
            metadata.append({
                "course_id": course_id,
                "course_code": course.code,
                "course_name": course.name,
                "university": course.university,
                "faculty": course.faculty,
                "section_heading": section["heading"],
                "section_content": section["content"],
                "department": course.department,
            })

    emb_array = np.vstack(all_embeddings)
    embedding_service.build_index(emb_array, metadata)


def collect_course_similarities(query_text: str) -> dict[str, float]:
    """Return {course_code: course-level average similarity} for one query,
    using the real comparison pipeline with a low cutoff so nothing is pruned."""
    response = compare_syllabus(query_text, custom_threshold=COLLECTION_THRESHOLD)
    return {c.course_code: c.average_similarity for c in response.top_courses}


def evaluate_threshold(
    per_query_sims: list[dict[str, float]],
    threshold: float,
    catalog_codes: list[str],
) -> Metrics:
    """Compute confusion counts over all (query, catalog-course) pairs."""
    tp = fp = fn = tn = 0
    for query, sims in zip(QUERIES, per_query_sims):
        for code in catalog_codes:
            predicted = sims.get(code, 0.0) >= threshold
            actual = code in query.expected_overlap
            if predicted and actual:
                tp += 1
            elif predicted and not actual:
                fp += 1
            elif not predicted and actual:
                fn += 1
            else:
                tn += 1
    return Metrics(threshold=threshold, tp=tp, fp=fp, fn=fn, tn=tn)


def run() -> dict:
    settings = get_settings()
    print(f"Model: {settings.MODEL_NAME}")
    print(f"Building index from {len(CATALOG)} catalog courses...")
    build_catalog_index(CATALOG)

    catalog_codes = [c.code for c in CATALOG]
    print(f"Running {len(QUERIES)} proposal queries through compare_syllabus...\n")

    per_query_sims: list[dict[str, float]] = []
    for query in QUERIES:
        sims = collect_course_similarities(query.text)
        per_query_sims.append(sims)
        ranked = sorted(sims.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_str = ", ".join(f"{code} {score:.2f}" for code, score in ranked) or "—"
        expected = ", ".join(sorted(query.expected_overlap)) or "(none)"
        print(f"  {query.name}")
        print(f"    expected overlap: {expected}")
        print(f"    top matches:      {top_str}")

    print("\n" + "=" * 64)
    print("THRESHOLD SWEEP (binary course-level overlap decision)")
    print("=" * 64)
    header = f"{'cutoff':>7} {'prec':>6} {'recall':>7} {'F1':>6} {'acc':>6}   TP/FP/FN/TN"
    print(header)
    print("-" * len(header))

    sweep: list[Metrics] = []
    for t in SWEEP_THRESHOLDS:
        m = evaluate_threshold(per_query_sims, t, catalog_codes)
        sweep.append(m)
        print(
            f"{m.threshold:>7.2f} {m.precision:>6.2f} {m.recall:>7.2f} "
            f"{m.f1:>6.2f} {m.accuracy:>6.2f}   {m.tp}/{m.fp}/{m.fn}/{m.tn}"
        )

    best = max(sweep, key=lambda m: (m.f1, m.precision))
    configured = settings.SIMILARITY_THRESHOLD
    print("-" * len(header))
    print(
        f"\nBest F1 at cutoff {best.threshold:.2f} "
        f"(F1={best.f1:.2f}, precision={best.precision:.2f}, recall={best.recall:.2f})."
    )
    nearest_to_configured = min(sweep, key=lambda m: abs(m.threshold - configured))
    print(
        f"Configured SIMILARITY_THRESHOLD={configured:.2f} → "
        f"F1={nearest_to_configured.f1:.2f}, "
        f"precision={nearest_to_configured.precision:.2f}, "
        f"recall={nearest_to_configured.recall:.2f}."
    )
    if abs(best.threshold - configured) > 1e-6:
        print(
            f"Suggestion: cutoff {best.threshold:.2f} scores higher F1 than the "
            f"configured {configured:.2f} on this benchmark."
        )

    return {
        "model": settings.MODEL_NAME,
        "configured_threshold": configured,
        "best_threshold": best.threshold,
        "sweep": [
            {
                "threshold": m.threshold,
                "precision": round(m.precision, 4),
                "recall": round(m.recall, 4),
                "f1": round(m.f1, 4),
                "accuracy": round(m.accuracy, 4),
                "tp": m.tp, "fp": m.fp, "fn": m.fn, "tn": m.tn,
            }
            for m in sweep
        ],
        "per_query": [
            {
                "query": q.name,
                "expected_overlap": sorted(q.expected_overlap),
                "similarities": {k: round(v, 4) for k, v in sims.items()},
            }
            for q, sims in zip(QUERIES, per_query_sims)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Overlap-detection evaluation harness")
    parser.add_argument("--json", metavar="PATH", help="Write full results as JSON")
    args = parser.parse_args()

    results = run()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nWrote JSON results to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
