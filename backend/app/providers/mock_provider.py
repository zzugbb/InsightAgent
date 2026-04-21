import re
import time
from typing import Iterator

from app.providers.base import ProviderResponse, ProviderUsage


class MockLLMProvider:
    def __init__(self, model: str = "mock-gpt", provider: str = "mock"):
        self.model = model
        self.provider = provider
        self._last_usage: ProviderUsage | None = None

    def generate(self, prompt: str) -> ProviderResponse:
        normalized_prompt = prompt.strip() or "empty prompt"
        if "[mock-error]" in normalized_prompt:
            raise RuntimeError("Mock provider forced error for SSE contract testing.")
        content = (
            "This is a mock response from InsightAgent. "
            f"Prompt received: {normalized_prompt}"
        )
        usage = ProviderUsage(
            prompt_tokens=_mock_estimate_token_count(normalized_prompt),
            completion_tokens=_mock_estimate_token_count(content),
            total_tokens=_mock_estimate_token_count(normalized_prompt)
            + _mock_estimate_token_count(content),
        )
        self._last_usage = usage
        return ProviderResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
        )

    def stream_generate(self, prompt: str) -> Iterator[str]:
        result = self.generate(prompt)
        self._last_usage = result.usage
        delay_sec = _mock_stream_delay_seconds(prompt)
        for token in result.content.split():
            if delay_sec > 0:
                time.sleep(delay_sec)
            yield f"{token} "

    def get_last_usage(self) -> ProviderUsage | None:
        return self._last_usage


def _mock_estimate_token_count(text: str) -> int:
    normalized = text.strip()
    if not normalized:
        return 0
    cjk_units = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", normalized))
    return max(1, cjk_units + latin_words)


def _mock_stream_delay_seconds(prompt: str) -> float:
    normalized = prompt.strip()
    if not normalized:
        return 0.0

    explicit_ms = re.search(r"\[mock-slow-ms=(\d{1,4})\]", normalized)
    if explicit_ms:
        return min(int(explicit_ms.group(1)), 1000) / 1000.0

    generic_slow = re.search(r"\[mock-slow(?:=(\d{1,4}))?\]", normalized)
    if not generic_slow:
        return 0.0

    ms_raw = generic_slow.group(1)
    if ms_raw is None:
        return 0.015
    return min(int(ms_raw), 1000) / 1000.0
