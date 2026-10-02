"""Evaluate retrieval source hit rate and answer keyword coverage.

Usage:
    python evaluation/evaluate_rag.py
    python evaluation/evaluate_rag.py --with-llm
"""
import argparse
import json
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Allow Gemini generation; default evaluation uses the RAG fallback.",
    )
    args = parser.parse_args()
    if not args.with_llm:
        os.environ["RAG_DISABLE_LLM"] = "1"

    from rag.query_rag import answer_question

    cases = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))
    source_hits = 0
    keyword_hits = 0
    keyword_total = 0

    for case in cases:
        result = answer_question(case["question"], crop=case.get("crop"))
        sources = {source.get("source") for source in result["sources"]}
        answer = result["answer"].lower()
        source_ok = case["expected_source"] in sources
        matched = sum(keyword.lower() in answer for keyword in case["keywords"])
        source_hits += source_ok
        keyword_hits += matched
        keyword_total += len(case["keywords"])
        print(
            f"[{ 'OK' if source_ok else 'FAIL' }] {case['question']} "
            f"(sources={len(sources)}, keywords={matched}/{len(case['keywords'])})"
        )

    source_rate = source_hits / len(cases) if cases else 0
    keyword_rate = keyword_hits / keyword_total if keyword_total else 0
    print(f"\nSource hit rate: {source_rate:.1%} ({source_hits}/{len(cases)})")
    print(f"Answer keyword coverage: {keyword_rate:.1%} ({keyword_hits}/{keyword_total})")
    return 0 if source_rate >= 0.8 and keyword_rate >= 0.6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
