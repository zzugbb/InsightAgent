from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str


class ProviderCallError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        user_message: str,
        detail: str | None = None,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message
        self.detail = detail
        self.status_code = status_code
        self.retryable = retryable


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> ProviderResponse:
        """Return a simple provider response for the given prompt."""

    def stream_generate(self, prompt: str) -> Iterator[str]:
        """Yield response chunks for SSE-style streaming."""
