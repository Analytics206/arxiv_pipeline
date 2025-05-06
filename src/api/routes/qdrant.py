from fastapi import APIRouter, HTTPException
import requests
import os

router = APIRouter()

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "arxiv_papers")

QDRANT_BASE_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

@router.get("/paper-stats", tags=["qdrant"])
def qdrant_paper_stats():
    """
    Returns stats for Qdrant collection: number of points (papers).
    """
    url = f"{QDRANT_BASE_URL}/collections/{QDRANT_COLLECTION}/stats"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        stats = resp.json()
        papers = stats.get("result", {}).get("points_count", 0)
        # Qdrant does not natively store authors/categories as fields; extend if schema supports it
        return {"papers": papers, "authors": 0, "categories": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant error: {str(e)}")
