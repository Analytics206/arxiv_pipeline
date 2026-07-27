"""Connection contract for the shared ai-services model servers."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse


def resolve_ollama_url(
    config: dict[str, Any] | None = None,
    *,
    explicit_url: str | None = None,
) -> str:
    """Resolve the native Ollama base URL for host or container consumers.

    Resolution order:
    1. explicit function/CLI value;
    2. ``OLLAMA_URL``;
    3. ``AI_SERVICES_OLLAMA_HOST`` or ``AI_SERVICES_HOST`` plus port;
    4. the local host and port in project configuration.

    The returned URL never includes ``/v1`` because the official Ollama Python
    client uses the native API at the service root.
    """

    direct_url = explicit_url or os.getenv("OLLAMA_URL")
    if direct_url:
        return _native_ollama_url(direct_url)

    ai_config = (config or {}).get("ai_services", {})
    host = (
        os.getenv("AI_SERVICES_OLLAMA_HOST")
        or os.getenv("AI_SERVICES_HOST")
        or ai_config.get("host_local")
        or "localhost"
    )
    port = int(
        os.getenv("AI_SERVICES_OLLAMA_PORT") or ai_config.get("ollama_port") or 11434
    )
    return _host_and_port_url(str(host), port)


def resolve_ollama_model(
    config: dict[str, Any] | None = None,
    *,
    explicit_model: str | None = None,
) -> str:
    """Resolve the consumer-selected model stored by shared ai-services."""

    return (
        explicit_model
        or os.getenv("OLLAMA_MODEL")
        or (config or {}).get("analysis", {}).get("model")
        or "qwen3.5:4b"
    )


def resolve_ollama_embedding_model(
    config: dict[str, Any] | None = None,
    *,
    explicit_model: str | None = None,
) -> str:
    """Resolve the project-selected embedding model stored by ai-services."""

    return (
        explicit_model
        or os.getenv("OLLAMA_EMBEDDING_MODEL")
        or (config or {}).get("research_index", {}).get("embedding_model")
        or "mxbai-embed-large:latest"
    )


def _host_and_port_url(host: str, port: int) -> str:
    raw = host.strip()
    if raw.endswith("://"):
        raise ValueError(f"Invalid ai-services host: {host!r}")
    value = raw.rstrip("/")
    if "://" not in value:
        value = f"http://{value}"
    parsed = urlparse(value)
    if not parsed.hostname:
        raise ValueError(f"Invalid ai-services host: {host!r}")
    if parsed.port is not None:
        return _native_ollama_url(value)

    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    return f"{parsed.scheme or 'http'}://{hostname}:{port}"


def _native_ollama_url(value: str) -> str:
    raw = value.strip()
    if not raw or raw.endswith("://"):
        raise ValueError("Ollama URL cannot be empty")
    url = raw.rstrip("/")
    if "://" not in url:
        url = f"http://{url}"
    if url.endswith("/v1"):
        url = url[:-3].rstrip("/")
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid Ollama URL: {value!r}")
    return url
