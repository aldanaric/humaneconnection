"""Rebuild or inspect the managed Humane Connection RAG index."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services import rag_index_manager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show whether the index matches the current source documents.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.status:
        status = rag_index_manager.get_status()
        if args.json:
            print(json.dumps(status.as_dict()))
        else:
            print(f"State: {status.state}")
            print(status.message)
            print(f"Source directory: {status.source_dir}")
            print(f"Index directory: {status.index_dir}")
            print(f"Source files: {status.source_files}")
            print(f"Indexed sources: {status.indexed_sources}")
            print(f"Chunks: {status.chunks}")
        raise SystemExit(0 if status.state == "ready" else 2)

    result = rag_index_manager.rebuild_index()
    summary = {
        "output_dir": str(result.output_dir),
        "source_files_seen": result.source_files_seen,
        "source_files_indexed": result.source_files_indexed,
        "duplicate_files_skipped": result.duplicate_files_skipped,
        "failed_files": result.failed_files,
        "chunks": result.chunks,
        "dense_dimensions": result.dense_dimensions,
        "sparse_dimensions": result.sparse_dimensions,
    }
    if args.json:
        print(json.dumps(summary))
    else:
        print("RAG rebuild completed.")
        for key, value in summary.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
