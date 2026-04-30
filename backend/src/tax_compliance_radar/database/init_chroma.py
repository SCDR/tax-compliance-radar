from __future__ import annotations

import chromadb

from tax_compliance_radar.config import CHROMA_COLLECTION_NAME, CHROMA_PATH


def main() -> None:
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={
            "description": "Thailand VAT regulations index",
            "embedding_model": "qwen3-embedding:0.6b",
            "language": "zh",
        },
    )
    print(f"Chroma collection initialized: {CHROMA_COLLECTION_NAME}")


if __name__ == "__main__":
    main()
