from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class Neo4jConnectionResponse(BaseModel):
    """Response model for Neo4j connection test"""
    status: str
    message: str
    databases: Optional[List[str]] = None

class Neo4jStats(BaseModel):
    """Response model for Neo4j database statistics"""
    papers: int
    authors: int
    categories: int
    error: Optional[str] = None

class Neo4jGraphResponse(BaseModel):
    """Response model for Neo4j graph data"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    error: Optional[str] = None
