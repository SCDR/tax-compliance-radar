from __future__ import annotations

import chromadb

from tax_compliance_radar.config import CHROMA_COLLECTION_NAME, CHROMA_PATH, settings


def main() -> None:
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={
            "description": settings.chroma_meta.description,
            "embedding_model": settings.embedding.model,
            "language": settings.chroma_meta.language,
        },
    )
    print(f"Chroma collection initialized: {CHROMA_COLLECTION_NAME}")


if __name__ == "__main__":
    main()
