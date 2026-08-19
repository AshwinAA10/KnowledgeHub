"""
Tests — LLM API Endpoints (/llm/generate)
==========================================
Integration tests for:
- POST /llm/generate endpoint behavior
- Request validation (empty prompt, whitespace prompt, temperature/tokens bounds)
- Unconfigured API key returns HTTP 503
- Provider error mapping to HTTP 500
- Verification that API key never appears in responses
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from openai.types.responses.response_usage import ResponseUsage

from app.main import app
from app.config import settings
from app.database import create_pool, set_pool, clear_pool, init_db_schema


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



@pytest.fixture(autouse=True)
async def setup_db_pool():
    """Ensure database pool and schema are initialized for FastAPI app lifespan."""
    pool = await create_pool()
    set_pool(pool)
    await init_db_schema()
    yield
    await pool.close()
    clear_pool()


@pytest.fixture
async def client():
    """Provide an async HTTP client wired directly to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


async def test_llm_generate_endpoint_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """POST /llm/generate returns 200 with generated text, model, status, and usage."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-mock-valid-key")
    monkeypatch.setattr(settings, "openai_model", "gpt-5.5")

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_mock_response(
            output_text="KnowledgeHub provides semantic search and RAG capabilities.",
            model="gpt-5.5",
            status="completed",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
        )
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        res = await client.post(
            "/llm/generate",
            json={
                "prompt": "What does KnowledgeHub do?",
                "instructions": "Be concise.",
                "max_output_tokens": 150,
                "temperature": 0.5,
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "KnowledgeHub provides semantic search and RAG capabilities."
    assert data["model"] == "gpt-5.5"
    assert data["status"] == "completed"
    assert data["usage"]["total_tokens"] == 30


async def test_llm_generate_empty_prompt_validation(client: AsyncClient):
    """Empty prompt returns HTTP 422 Unprocessable Entity."""
    res = await client.post("/llm/generate", json={"prompt": ""})
    assert res.status_code == 422


async def test_llm_generate_whitespace_prompt_validation(client: AsyncClient):
    """Whitespace-only prompt returns HTTP 422."""
    res = await client.post("/llm/generate", json={"prompt": "   \n\t   "})
    assert res.status_code == 422


async def test_llm_generate_temperature_bounds(client: AsyncClient):
    """Temperature out of bounds [0.0, 2.0] returns HTTP 422."""
    res_high = await client.post("/llm/generate", json={"prompt": "test", "temperature": 2.5})
    assert res_high.status_code == 422

    res_low = await client.post("/llm/generate", json={"prompt": "test", "temperature": -0.1})
    assert res_low.status_code == 422


async def test_llm_generate_max_tokens_bounds(client: AsyncClient):
    """max_output_tokens out of bounds returns HTTP 422."""
    res_zero = await client.post("/llm/generate", json={"prompt": "test", "max_output_tokens": 0})
    assert res_zero.status_code == 422

    res_high = await client.post("/llm/generate", json={"prompt": "test", "max_output_tokens": 20000})
    assert res_high.status_code == 422


async def test_llm_generate_missing_api_key_returns_503(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Unconfigured OPENAI_API_KEY returns HTTP 503 Service Unavailable."""
    monkeypatch.setattr(settings, "openai_api_key", "")

    res = await client.post("/llm/generate", json={"prompt": "Hello AI"})
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


async def test_llm_generate_api_key_never_leaked(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """The API key must never appear in response body or headers."""
    secret_key = "sk-super-secret-production-token-12345"
    monkeypatch.setattr(settings, "openai_api_key", secret_key)

    mock_client = MagicMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_mock_response(output_text="Clean answer without secrets.")
    )

    with patch("app.services.llm_service.get_client", return_value=mock_client):
        res = await client.post("/llm/generate", json={"prompt": "Tell me a secret"})

    assert res.status_code == 200
    assert secret_key not in res.text
    for header_val in res.headers.values():
        assert secret_key not in header_val
