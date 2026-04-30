from __future__ import annotations

import time

import ollama

from tax_compliance_radar.config import settings


def main() -> None:
    client = ollama.Client(host=settings.llm.base_url)
    started = time.perf_counter()
    res = client.embeddings(model=settings.llm.embedding_model, prompt="泰国VAT合规")
    elapsed_ms = (time.perf_counter() - started) * 1000
    vec = res.get("embedding", [])
    print(f"ok model={settings.llm.embedding_model} dim={len(vec)} latency_ms={elapsed_ms:.1f}")


if __name__ == "__main__":
    main()
