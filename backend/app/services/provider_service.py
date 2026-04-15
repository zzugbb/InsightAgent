from app.providers.base import LLMProvider
from app.providers.mock_provider import MockLLMProvider
from app.providers.openai_compatible_provider import OpenAICompatibleLLMProvider
from app.services.settings_service import get_stored_settings


class ProviderSelectionError(RuntimeError):
    def __init__(self, *, code: str, user_message: str):
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


def get_llm_provider(user_id: str) -> LLMProvider:
    settings = get_stored_settings(user_id)
    if settings.mode == "mock":
        return MockLLMProvider(
            model=settings.model,
            provider=settings.provider,
        )

    if settings.mode != "remote":
        raise ProviderSelectionError(
            code="invalid_runtime_mode",
            user_message=f"Unsupported runtime mode: {settings.mode}",
        )

    if not (settings.api_key or "").strip():
        raise ProviderSelectionError(
            code="remote_api_key_required",
            user_message="Remote 模式需要先配置 API Key，请在设置中补全后再发送。",
        )

    if not (settings.base_url or "").strip():
        raise ProviderSelectionError(
            code="remote_base_url_required",
            user_message="Remote 模式需要先配置 Base URL，请在设置中补全后再发送。",
        )

    return OpenAICompatibleLLMProvider(
        model=settings.model,
        provider=settings.provider,
        base_url=settings.base_url or "",
        api_key=settings.api_key or "",
    )
