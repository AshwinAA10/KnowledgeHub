"""
Tests — LLM Service (OpenAI Responses API)
===========================================
Unit tests for the LLM service layer:
- Successful text generation with normalized response
- Parameter forwarding (prompt, instructions, max_output_tokens, temperature)
- Missing API key handling (status_hint=503)
- Provider error mapping (AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, APIStatusError)
- Runtime LLM info metadata
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import openai
from openai.types.responses.response_usage import ResponseUsage

from app.config import settings
from app.services.llm_service import (
    LLMServiceError,
    generate_response,
    get_llm_info,
)


def _make_mock_response(
    output_text: str = "Test response text",
    model: str = "gpt-5.5",
    status: str = "completed",
    input_tokens: int = 15,
    output_tokens: int = 25,
    total_tokens: int = 40,
) -> MagicMock:
    """Helper creating a mock Responses API return object."""
    mock_resp = MagicMock()
    mock_resp.output_text = output_text
    mock_resp.model = model
    mock_resp.status = status
    mock_resp.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )
    return mock_resp



@pytest.mark.asyncio
async def test_generate_response_success(monkeypatch: pytest.MonkeyPatch):
    """Successful generation returns normalized text, model, status, and usage."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-valid-key")
    monkeypatch.setattr(settings, "openai_model", "gpt-5.5")

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_mock_response(
            output_text="Vector databases index embeddings for similarity search.",
            model="gpt-5.5",
            status="completed",
            input_tokens=12,
            output_tokens=28,
            total_tokens=40,
        )
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        result = await generate_response(prompt="What is a vector database?")

    assert result["text"] == "Vector databases index embeddings for similarity search."
    assert result["model"] == "gpt-5.5"
    assert result["status"] == "completed"
    assert result["usage"] == {
        "input_tokens": 12,
        "output_tokens": 28,
        "total_tokens": 40,
    }


@pytest.mark.asyncio
async def test_generate_response_forwards_parameters(monkeypatch: pytest.MonkeyPatch):
    """Service forwards prompt, instructions, max_output_tokens, and temperature."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-valid-key")

    mock_client = MagicMock()
    mock_create = AsyncMock(return_value=_make_mock_response())
    mock_client.responses.create = mock_create

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        await generate_response(
            prompt="Summarize pgvector",
            instructions="Be concise",
            max_output_tokens=100,
            temperature=0.3,
        )

    mock_create.assert_called_once_with(
        model=settings.openai_model,
        input="Summarize pgvector",
        instructions="Be concise",
        max_output_tokens=100,
        temperature=0.3,
    )


@pytest.mark.asyncio
async def test_generate_missing_api_key(monkeypatch: pytest.MonkeyPatch):
    """Missing or empty OPENAI_API_KEY raises LLMServiceError with status_hint=503."""
    monkeypatch.setattr(settings, "openai_api_key", "")

    with pytest.raises(LLMServiceError) as exc_info:
        await generate_response(prompt="Test prompt")

    assert exc_info.value.status_hint == 503
    assert "not configured" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_generate_authentication_error(monkeypatch: pytest.MonkeyPatch):
    """OpenAI AuthenticationError maps to LLMServiceError with status_hint=503."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-invalid-key")

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="Incorrect API key provided",
            response=MagicMock(),
            body=None,
        )
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        with pytest.raises(LLMServiceError) as exc_info:
            await generate_response(prompt="Test prompt")

    assert exc_info.value.status_hint == 503
    assert "authentication failed" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_generate_rate_limit_error(monkeypatch: pytest.MonkeyPatch):
    """OpenAI RateLimitError maps to LLMServiceError with status_hint=503."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-key")

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        side_effect=openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=None,
        )
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        with pytest.raises(LLMServiceError) as exc_info:
            await generate_response(prompt="Test prompt")

    assert exc_info.value.status_hint == 503
    assert "rate limit" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_generate_timeout_error(monkeypatch: pytest.MonkeyPatch):
    """OpenAI APITimeoutError maps to LLMServiceError with status_hint=500."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-key")

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        side_effect=openai.APITimeoutError(request=MagicMock())
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        with pytest.raises(LLMServiceError) as exc_info:
            await generate_response(prompt="Test prompt")

    assert exc_info.value.status_hint == 500
    assert "timed out" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_generate_connection_error(monkeypatch: pytest.MonkeyPatch):
    """OpenAI APIConnectionError maps to LLMServiceError with status_hint=500."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-key")

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        side_effect=openai.APIConnectionError(request=MagicMock())
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        with pytest.raises(LLMServiceError) as exc_info:
            await generate_response(prompt="Test prompt")

    assert exc_info.value.status_hint == 500
    assert "connection" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_generate_status_error(monkeypatch: pytest.MonkeyPatch):
    """OpenAI APIStatusError maps to LLMServiceError with status_hint=500."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-key")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_client.responses.create = AsyncMock(
        side_effect=openai.APIStatusError(
            message="Internal Server Error",
            response=mock_resp,
            body=None,
        )
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        with pytest.raises(LLMServiceError) as exc_info:
            await generate_response(prompt="Test prompt")

    assert exc_info.value.status_hint == 500
    assert "500" in exc_info.value.message


def test_get_llm_info(monkeypatch: pytest.MonkeyPatch):
    """Runtime LLM info reports model, timeout, max_retries, and api_configured flag."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-key")
    monkeypatch.setattr(settings, "openai_model", "gpt-5.5")
    monkeypatch.setattr(settings, "openai_request_timeout", 45.0)
    monkeypatch.setattr(settings, "openai_max_retries", 3)

    info = get_llm_info()
    assert info["model"] == "gpt-5.5"
    assert info["timeout"] == 45.0
    assert info["max_retries"] == 3
    assert info["api_configured"] is True
