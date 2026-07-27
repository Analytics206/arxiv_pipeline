from src.analysis.cache import JsonChunkAnalysisCache
from src.analysis.models import ChunkAnalysisDraft


def test_chunk_cache_round_trip_and_identity_isolation(tmp_path):
    cache = JsonChunkAnalysisCache(tmp_path)
    draft = ChunkAnalysisDraft(concepts=["agent harness"])
    identity = {
        "document_hash": "a" * 64,
        "chunk_id": "chunk-1",
        "model": "qwen3.5:4b",
        "prompt_version": "agent-paper-v1",
    }

    path = cache.put(draft, **identity)

    assert path.is_file()
    assert cache.get(**identity) == draft
    assert cache.get(**{**identity, "model": "qwen3.5:2b"}) is None
