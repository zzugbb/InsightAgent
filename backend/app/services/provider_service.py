from app.providers.base import LLMProvider
from app.providers.mock_provider import MockLLMProvider
from app.services.settings_service import get_stored_settings


def get_llm_provider() -> LLMProvider:
    settings = get_stored_settings()
    if settings.mode == "mock":
        return MockLLMProvider(
            model=settings.model,
            provider=settings.provider,
        )

    # Remote provider will be introduced later after the mock-first W1 flow is stable.
    return MockLLMProvider(
        model=settings.model,
        provider=settings.provider,
    )
