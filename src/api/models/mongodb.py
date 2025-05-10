from pydantic import BaseModel
from typing import Dict, List, Optional

class MongoDBStats(BaseModel):
    """Response model for MongoDB paper statistics"""
    papers: int
    authors: int
    categories: int
    error: Optional[str] = None

class MongoDBConnectionResponse(BaseModel):
    """Response model for MongoDB connection test"""
    status: str
    message: str
    databases: Optional[List[str]] = None

class CategoryCount(BaseModel):
    """Model for category count data"""
    count: int
    percentage: float

class PaperAnalysisResponse(BaseModel):
    """Response model for paper analysis by time"""
    yearly: Dict[str, int]
    monthly: Dict[str, int]
    daily: Dict[str, int]
    total_papers: int
    categories: List[Dict[str, str]]
    error: Optional[str] = None
