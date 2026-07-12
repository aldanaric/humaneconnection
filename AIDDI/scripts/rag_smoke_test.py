"""Verify managed-index status, loading, and representative retrieval results."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services import rag, rag_index_manager


def main() -> None:
    status = rag_index_manager.get_status()
    if status.state != "ready":
        raise SystemExit(f"RAG index is not current: {status.message}")

    queries = [
        "What should a facilitator do after a serious workplace disclosure?",
        "What belongs in a 30-day growth plan?",
        "How do personality Roles and Strategies differ?",
    ]

    if not rag.is_available():
        raise SystemExit("RAG index is unavailable.")

    for query in queries:
        results = rag.retrieve(query, top_k=3)
        if not results:
            raise SystemExit(f"No RAG results for: {query}")

        print(f"\nQUERY: {query}")
        for result in results:
            print(
                f"  {result['score']:.3f} | {result['source']} | "
                f"{result['location']}"
            )

    print(
        f"\nRAG smoke test passed: {status.indexed_sources} indexed sources, "
        f"{status.chunks} chunks."
    )


if __name__ == "__main__":
    main()
