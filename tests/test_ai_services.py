import pytest

from src.utils.ai_services import (
    resolve_ollama_embedding_model,
    resolve_ollama_model,
    resolve_ollama_url,
)


def test_explicit_ollama_url_wins_and_removes_openai_path(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ignored:1234")

    result = resolve_ollama_url(
        explicit_url="http://gpu-box:11434/v1",
    )

    assert result == "http://gpu-box:11434"


def test_shared_service_host_and_port_come_from_environment(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.setenv("AI_SERVICES_HOST", "research-gpu")
    monkeypatch.setenv("AI_SERVICES_OLLAMA_PORT", "22468")

    assert resolve_ollama_url() == "http://research-gpu:22468"


def test_local_config_is_the_final_url_fallback(monkeypatch):
    for name in (
        "OLLAMA_URL",
        "AI_SERVICES_OLLAMA_HOST",
        "AI_SERVICES_HOST",
        "AI_SERVICES_OLLAMA_PORT",
    ):
        monkeypatch.delenv(name, raising=False)

    result = resolve_ollama_url(
        {"ai_services": {"host_local": "localhost", "ollama_port": 11434}}
    )

    assert result == "http://localhost:11434"


def test_model_selection_prefers_project_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:2b")

    result = resolve_ollama_model(
        {"analysis": {"model": "qwen3.5:4b"}},
    )

    assert result == "qwen3.5:2b"


def test_embedding_model_selection_prefers_project_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b")

    result = resolve_ollama_embedding_model(
        {"research_index": {"embedding_model": "mxbai-embed-large:latest"}},
    )

    assert result == "qwen3-embedding:0.6b"


def test_invalid_service_host_is_rejected(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.setenv("AI_SERVICES_HOST", "http://")

    with pytest.raises(ValueError, match="Invalid ai-services host"):
        resolve_ollama_url()
