"""HTTP client for the canonical REST research contracts."""

from __future__ import annotations

import os
from types import TracebackType
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_RESEARCH_API_URL = "http://localhost:8000"


class ResearchApiError(RuntimeError):
    """An actionable error returned by the canonical research API."""

    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Research API returned HTTP {status_code}: {detail}")


class ResearchApiClient:
    """Small async client that deliberately mirrors GET-only API operations."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = resolve_research_api_url(base_url)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={"User-Agent": "arxiv-research-mcp/0.8.0"},
        )

    async def __aenter__(self) -> "ResearchApiClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(path, params=_clean_params(params))
        if response.is_error:
            raise ResearchApiError(
                status_code=response.status_code,
                detail=_response_detail(response),
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise ResearchApiError(
                status_code=response.status_code,
                detail="Response was not valid JSON",
            ) from error
        if not isinstance(payload, dict):
            raise ResearchApiError(
                status_code=response.status_code,
                detail="Response was not a JSON object",
            )
        return payload

    async def close(self) -> None:
        await self._client.aclose()


def resolve_research_api_url(explicit_url: str | None = None) -> str:
    """Resolve and validate the REST service used by the MCP adapter."""

    value = explicit_url or os.getenv(
        "RESEARCH_API_URL",
        DEFAULT_RESEARCH_API_URL,
    )
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "RESEARCH_API_URL must be an absolute http(s) URL without "
            "parameters, query, or fragment"
        )
    return normalized


def _clean_params(
    params: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if params is None:
        return None
    return {key: value for key, value in params.items() if value is not None}


def _response_detail(response: httpx.Response) -> Any:
    try:
        payload = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    return payload.get("detail", payload) if isinstance(payload, dict) else payload
