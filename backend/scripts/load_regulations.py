from __future__ import annotations

import argparse
from pathlib import Path

from tax_compliance_radar.config import REGULATIONS_DIR
from tax_compliance_radar.database.regulation_loader import load_regulations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load regulation markdown files into Chroma and SQLite")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=REGULATIONS_DIR,
        help="Directory containing regulation markdown files",
    )
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--chunk-overlap", type=int, default=50)
    parser.add_argument("--reset", action="store_true", help="Reset Chroma collection before loading")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = load_regulations(
        source_dir=args.source_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        reset_collection=args.reset,
    )
    print(
        "loaded docs={docs} chunks={chunks} collection={collection} source={source_dir}".format(**stats)
    )


if __name__ == "__main__":
    main()
