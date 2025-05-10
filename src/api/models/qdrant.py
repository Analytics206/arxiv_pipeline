from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class QdrantStats(BaseModel):
    """Response model for Qdrant paper statistics"""
    papers: int    # Shows number of vector embeddings stored (paper count)
    authors: int   # Shows vector dimensions (typically 768)
    categories: int  # Shows total collection count
    error: Optional[str] = None

class QdrantConnectionResponse(BaseModel):
    """Response model for Qdrant connection test"""
    status: str
    message: str
    collections: Optional[List[str]] = None
    version: Optional[str] = None

class SyncResponse(BaseModel):
    """Response model for sync operations"""
    status: str
    message: str
    process_id: Optional[str] = None

class SyncStatusResponse(BaseModel):
    """Response model for sync status check"""
    status: str
    exit_code: Optional[int] = None
    message: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
