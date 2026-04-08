from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> ProviderResponse:
        """Return a simple provider response for the given prompt."""

    def stream_generate(self, prompt: str) -> Iterator[str]:
        """Yield response chunks for SSE-style streaming."""
