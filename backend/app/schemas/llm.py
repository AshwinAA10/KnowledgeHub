"""
KnowledgeHub — LLM Schemas
==========================
Pydantic models for LLM generation requests and responses using the OpenAI Responses API.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMGenerateRequest(BaseModel):
    """Payload for POST /llm/generate."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User prompt or input text for LLM generation",
    )
    instructions: str | None = Field(
        default=None,
        max_length=4000,
        description="Optional system instructions guiding generation behavior",
    )
    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        le=16384,
        description="Optional upper bound on output token generation",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional sampling temperature",
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Prompt string must not be empty or whitespace only.")
        return trimmed


class LLMUsage(BaseModel):
    """Token consumption statistics from LLM generation."""
    model_config = ConfigDict(from_attributes=True)

    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMGenerateResponse(BaseModel):
    """Normalized response returned from LLM text generation."""
    model_config = ConfigDict(from_attributes=True)

    text: str
    model: str
    status: str
    usage: LLMUsage | None = None
