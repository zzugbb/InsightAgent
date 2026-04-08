from typing import Iterator

from app.providers.base import ProviderResponse


class MockLLMProvider:
    def __init__(self, model: str = "mock-gpt", provider: str = "mock"):
        self.model = model
        self.provider = provider

    def generate(self, prompt: str) -> ProviderResponse:
        normalized_prompt = prompt.strip() or "empty prompt"
        content = (
            "This is a mock response from InsightAgent. "
            f"Prompt received: {normalized_prompt}"
        )
        return ProviderResponse(
            content=content,
            model=self.model,
            provider=self.provider,
        )

    def stream_generate(self, prompt: str) -> Iterator[str]:
        result = self.generate(prompt)
        for token in result.content.split():
            yield f"{token} "
