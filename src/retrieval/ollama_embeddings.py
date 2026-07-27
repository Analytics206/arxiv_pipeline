"""Shared-Ollama embedding adapter."""

from __future__ import annotations

from collections.abc import Sequence


class OllamaEmbeddingModel:
    """Generate document and query embeddings through the shared Ollama server."""

    def __init__(
        self,
        *,
        model_name: str,
        host: str,
        query_prefix: str = (
            "Represent this sentence for searching relevant passages: "
        ),
        document_prefix: str = "",
    ):
        from ollama import Client

        self.model_name = model_name
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self._client = Client(host=host, timeout=600)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(
            [f"{self.document_prefix}{text}" for text in texts]
        )

    def embed_query(self, query: str) -> list[float]:
        return self._embed([f"{self.query_prefix}{query}"])[0]

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        response = self._client.embed(model=self.model_name, input=inputs)
        embeddings = (
            response["embeddings"]
            if isinstance(response, dict)
            else response.embeddings
        )
        vectors = [list(vector) for vector in embeddings]
        if len(vectors) != len(inputs) or any(not vector for vector in vectors):
            raise RuntimeError(
                f"{self.model_name} returned an invalid embedding response"
            )
        return vectors
