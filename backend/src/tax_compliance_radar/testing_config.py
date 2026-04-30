from __future__ import annotations

from tax_compliance_radar.config import LLMBackendConfig, Settings

TEST_SETTINGS = Settings(
    llm=LLMBackendConfig(
        model="llama3.2",
        fallback_models=("qwen2.5",),
        generation_format="json",
        generation_temperature=0.0,
        generation_num_predict=128,
        generation_think=False,
    )
)
