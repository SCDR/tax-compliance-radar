from __future__ import annotations

import time

import ollama

from tax_compliance_radar.config import settings


def main() -> None:
    client = ollama.Client(host=settings.llm.base_url)
    candidates = (settings.llm.model, *settings.llm.fallback_models)

    for model in candidates:
        started = time.perf_counter()
        try:
            res = client.generate(
                model=model,
                prompt="用一句中文回答：泰国VAT注册要点。",
                options={"temperature": 0.0, "num_predict": 40},
                think=False,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            text = (res.get("response") or "").strip().replace("\n", " ")[:60]
            print(f"ok model={model} latency_ms={elapsed_ms:.1f} preview={text}")
            return
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - started) * 1000
            print(f"fail model={model} latency_ms={elapsed_ms:.1f} error={exc}")

    raise SystemExit("No local Ollama model available.")


if __name__ == "__main__":
    main()
