"""Recoverable cache for expensive model-generated chunk drafts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.analysis.models import ChunkAnalysisDraft


class JsonChunkAnalysisCache:
    """Store validated chunk drafts as ignored, rebuildable JSON files."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def get(
        self,
        *,
        document_hash: str,
        chunk_id: str,
        model: str,
        prompt_version: str,
    ) -> ChunkAnalysisDraft | None:
        path = self._path(
            document_hash=document_hash,
            chunk_id=chunk_id,
            model=model,
            prompt_version=prompt_version,
        )
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ChunkAnalysisDraft.model_validate(payload["draft"])
        except (KeyError, OSError, ValueError, json.JSONDecodeError):
            return None

    def put(
        self,
        draft: ChunkAnalysisDraft,
        *,
        document_hash: str,
        chunk_id: str,
        model: str,
        prompt_version: str,
    ) -> Path:
        path = self._path(
            document_hash=document_hash,
            chunk_id=chunk_id,
            model=model,
            prompt_version=prompt_version,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "document_hash": document_hash,
            "chunk_id": chunk_id,
            "model": model,
            "prompt_version": prompt_version,
            "draft": draft.model_dump(mode="json"),
        }
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
        return path

    def _path(
        self,
        *,
        document_hash: str,
        chunk_id: str,
        model: str,
        prompt_version: str,
    ) -> Path:
        raw_key = f"{document_hash}:{chunk_id}:{model}:{prompt_version}".encode()
        cache_key = hashlib.sha256(raw_key).hexdigest()
        return self.directory / document_hash[:16] / f"{cache_key}.json"
