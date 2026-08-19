"""
KnowledgeHub — LLM Routes
=========================
FastAPI endpoints for standalone LLM text generation using the OpenAI Responses API.
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse
from app.services import llm_service
from app.services.llm_service import LLMServiceError

router = APIRouter(prefix="/llm", tags=["LLM"])


@router.post(
    "/generate",
    response_model=LLMGenerateResponse,
    summary="Generate text via the OpenAI Responses API",
)
async def generate_llm_text(
    request: LLMGenerateRequest,
) -> LLMGenerateResponse:
    """
    Generate text completion for a given prompt and optional instructions.

    - Uses the configured OpenAI model (default: gpt-5.5) via Responses API.
    - Returns generated text, model identifier, execution status, and usage statistics.
    - Sanitizes provider-level errors and returns appropriate HTTP status codes (503 / 500).
    """
    try:
        response_data = await llm_service.generate_response(
            prompt=request.prompt,
            instructions=request.instructions,
            max_output_tokens=request.max_output_tokens,
            temperature=request.temperature,
        )
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=exc.status_hint,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unhandled error during LLM generation: {exc}",
        ) from exc

    return LLMGenerateResponse(**response_data)
