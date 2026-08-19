"""
KnowledgeHub — LLM Service (OpenAI Responses API)
=================================================
Dedicated service for generating text via the modern OpenAI Responses API.
Handles API client initialization, structured parameter forwarding,
response normalization, and provider error isolation.

Design Principles:
- Uses the modern Responses API (`client.responses.create`) rather than legacy Chat Completions.
- Uses `AsyncOpenAI` for non-blocking async execution.
- Decoupled from document search, vector storage, and RAG (those belong to later milestones).
- Optional API key at startup: Missing key raises `LLMServiceError` with status_hint=503
  when invoked, allowing server startup and database-only test runs without credentials.
- Provider errors are sanitized to prevent secret or raw payload leakage.
- Note on streaming: Token-by-token streaming is intentionally deferred to the RAG/chat milestone.
"""

from typing import Any
import openai
from openai import AsyncOpenAI

from app.config import settings


class LLMServiceError(Exception):
    """
    Exception raised when LLM generation fails.

    Attributes:
        message: Sanitized human-readable error description.
        status_hint: Suggested HTTP status code (e.g. 503 for auth/rate/config, 500 for provider errors).
    """

    def __init__(self, message: str, status_hint: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_hint = status_hint


def get_client() -> AsyncOpenAI:
    """
    Instantiate an AsyncOpenAI client configured from application settings.

    Raises:
        LLMServiceError: If OPENAI_API_KEY is not configured (status_hint=503).
    """
    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise LLMServiceError(
            "OpenAI API key is not configured. Please set OPENAI_API_KEY in the backend environment.",
            status_hint=503,
        )

    return AsyncOpenAI(
        api_key=api_key,
        timeout=settings.openai_request_timeout,
        max_retries=settings.openai_max_retries,
    )


async def generate_response(
    prompt: str,
    instructions: str | None = None,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """
    Generate a text response using the OpenAI Responses API.

    Args:
        prompt: User input prompt.
        instructions: Optional system instructions guiding generation.
        max_output_tokens: Optional limit on generated output tokens.
        temperature: Optional sampling temperature.

    Returns:
        Normalized dictionary matching the LLMGenerateResponse schema:
        {
            "text": str,
            "model": str,
            "status": str,
            "usage": {"input_tokens": int, "output_tokens": int, "total_tokens": int} | None
        }

    Raises:
        LLMServiceError: On missing credentials, authentication failure, timeouts, or API errors.
    """
    client = get_client()

    # Build request kwargs for client.responses.create
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "input": prompt,
    }

    if instructions is not None:
        kwargs["instructions"] = instructions
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = await client.responses.create(**kwargs)

        # Extract output text
        output_text = getattr(response, "output_text", "")
        if not output_text and hasattr(response, "output") and response.output:
            # Fallback output aggregation if output_text property is not populated
            chunks = []
            for item in response.output:
                if getattr(item, "type", None) == "message" and hasattr(item, "content"):
                    for content_item in item.content:
                        if getattr(content_item, "type", None) == "output_text":
                            chunks.append(getattr(content_item, "text", ""))
            output_text = "".join(chunks)

        # Extract usage metrics if present
        usage_data = None
        if hasattr(response, "usage") and response.usage is not None:
            usage_data = {
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        return {
            "text": output_text,
            "model": getattr(response, "model", settings.openai_model) or settings.openai_model,
            "status": getattr(response, "status", "completed") or "completed",
            "usage": usage_data,
        }

    except LLMServiceError:
        raise
    except openai.AuthenticationError as exc:
        raise LLMServiceError(
            "LLM provider authentication failed. Please verify your OPENAI_API_KEY.",
            status_hint=503,
        ) from exc
    except openai.RateLimitError as exc:
        raise LLMServiceError(
            "LLM provider rate limit exceeded. Please retry after a brief delay.",
            status_hint=503,
        ) from exc
    except openai.APITimeoutError as exc:
        raise LLMServiceError(
            "LLM provider request timed out.",
            status_hint=500,
        ) from exc
    except openai.APIConnectionError as exc:
        raise LLMServiceError(
            "Failed to establish connection to LLM provider.",
            status_hint=500,
        ) from exc
    except openai.APIStatusError as exc:
        raise LLMServiceError(
            f"LLM provider returned an error (status code: {exc.status_code}).",
            status_hint=500,
        ) from exc
    except Exception as exc:
        raise LLMServiceError(
            f"Unexpected error during LLM generation: {exc}",
            status_hint=500,
        ) from exc


def get_llm_info() -> dict[str, Any]:
    """Return runtime metadata about the LLM service configuration."""
    return {
        "model": settings.openai_model,
        "timeout": settings.openai_request_timeout,
        "max_retries": settings.openai_max_retries,
        "api_configured": bool(settings.openai_api_key.strip()),
    }
