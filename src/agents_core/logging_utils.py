# Logging setup and utilities
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import os
import sys
from collections import defaultdict, OrderedDict
import pandas as pd
import numpy as np
import pymongo
from pymongo.errors import PyMongoError
from bson import ObjectId

# Configure root logger
def setup_logger(name: str, log_level: str = 'INFO') -> logging.Logger:
    """
    Configure a logger with the specified name and log level.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    level = getattr(logging, log_level.upper())
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(level)
    return logger

# Initialize default logger
logger = setup_logger('arxiv_pipeline')

# MongoDB Data Validation Functions
def validate_paper_schema(paper: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a paper document against the expected schema.
    
    Args:
        paper: Paper document dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    required_fields = ['id', 'title', 'authors', 'categories', 'published', 'pdf_url']
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in paper:
            errors.append(f"Missing required field: {field}")
    
    # Validate field types
    if 'id' in paper and not isinstance(paper['id'], str):
        errors.append("Field 'id' must be a string")
    
    if 'title' in paper and not isinstance(paper['title'], str):
        errors.append("Field 'title' must be a string")
    
    if 'authors' in paper:
        if not isinstance(paper['authors'], list):
            errors.append("Field 'authors' must be a list")
        elif not all(isinstance(author, str) for author in paper['authors']):
            errors.append("All authors must be strings")
    
    if 'categories' in paper:
        if not isinstance(paper['categories'], list):
            errors.append("Field 'categories' must be a list")
        elif not all(isinstance(cat, str) for cat in paper['categories']):
            errors.append("All categories must be strings")
    
    if 'published' in paper:
        if not isinstance(paper['published'], str):
            errors.append("Field 'published' must be a string")
        else:
            # Validate date format YYYY-MM-DDThh:mm:ssZ
            try:
                datetime.strptime(paper['published'], "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append("Field 'published' has invalid date format. Expected YYYY-MM-DDThh:mm:ssZ")
    
    if 'pdf_url' in paper and not isinstance(paper['pdf_url'], str):
        errors.append("Field 'pdf_url' must be a string")
    
    return len(errors) == 0, errors

def validate_publication_date(date_str: str) -> Tuple[bool, Optional[datetime]]:
    """
    Validate a publication date string and convert to datetime object.
    
    Args:
        date_str: ISO-format date string (YYYY-MM-DDThh:mm:ssZ)
        
    Returns:
        Tuple of (is_valid, datetime_obj or None)
    """
    if not isinstance(date_str, str):
        return False, None
    
    try:
        # Handle different date string formats
        if 'T' in date_str and 'Z' in date_str:
            # Standard ISO format: YYYY-MM-DDThh:mm:ssZ
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        elif 'T' in date_str:
            # ISO without Z: YYYY-MM-DDThh:mm:ss
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        elif len(date_str) == 10:
            # Just date: YYYY-MM-DD
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            return False, None
        
        # Validate date range (papers shouldn't be from future or too distant past)
        now = datetime.utcnow()
        if dt > now:
            return False, None
        if dt < datetime(1990, 1, 1):  # ArXiv didn't exist before 1991
            return False, None
            
        return True, dt
    except ValueError:
        return False, None

# Data Analysis Utilities
def count_papers_by_date(mongo_collection, date_field="published", group_by="day"):
    """
    Count papers by publication date with flexible grouping.
    
    Args:
        mongo_collection: MongoDB collection object
        date_field: Field name containing the date
        group_by: Grouping level ('day', 'month', 'year', 'weekday')
        
    Returns:
        OrderedDict of date counts
    """
    # Validate group_by parameter
    valid_groups = ['day', 'month', 'year', 'weekday']
    if group_by not in valid_groups:
        raise ValueError(f"group_by must be one of {valid_groups}")
    
    pipeline = []
    
    # Extract date components based on string format
    if group_by == 'day':
        pipeline.extend([
            {"$addFields": {"dateStr": {"$substr": [f"${date_field}", 0, 10]}}},
            {"$group": {"_id": "$dateStr", "count": {"$sum": 1}}}
        ])
    elif group_by == 'month':
        pipeline.extend([
            {"$addFields": {"yearMonth": {"$substr": [f"${date_field}", 0, 7]}}},
            {"$group": {"_id": "$yearMonth", "count": {"$sum": 1}}}
        ])
    elif group_by == 'year':
        pipeline.extend([
            {"$addFields": {"year": {"$substr": [f"${date_field}", 0, 4]}}},
            {"$group": {"_id": "$year", "count": {"$sum": 1}}}
        ])
    elif group_by == 'weekday':
        # This requires date conversion in Python
        results = list(mongo_collection.find({}, {date_field: 1}))
        weekday_counts = defaultdict(int)
        
        for doc in results:
            date_str = doc.get(date_field)
            if date_str and isinstance(date_str, str):
                try:
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    weekday = dt.strftime("%A")  # Full weekday name
                    weekday_counts[weekday] += 1
                except ValueError:
                    continue
        
        # Order by day of week
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                        "Friday", "Saturday", "Sunday"]
        ordered_counts = OrderedDict()
        for day in weekday_order:
            ordered_counts[day] = weekday_counts.get(day, 0)
        
        return ordered_counts
    
    # Execute aggregation for non-weekday queries
    pipeline.append({"$sort": {"_id": 1}})
    result = mongo_collection.aggregate(pipeline)
    
    # Convert to ordered dictionary
    counts = OrderedDict()
    for doc in result:
        counts[doc["_id"]] = doc["count"]
    
    return counts

def analyze_mongodb_collection(mongo_collection, query=None, projection=None):
    """
    Analyze the structure and content of a MongoDB collection.
    
    Args:
        mongo_collection: MongoDB collection object
        query: Optional filter query
        projection: Optional field projection
        
    Returns:
        Dictionary with analysis results
    """
    if query is None:
        query = {}
    
    analysis = {
        "collection_name": mongo_collection.name,
        "document_count": mongo_collection.count_documents(query),
        "fields": defaultdict(set),
        "field_types": defaultdict(set),
        "field_stats": {},
    }
    
    # Sample documents to analyze structure
    sample_size = min(1000, analysis["document_count"])
    if sample_size == 0:
        return analysis
    
    cursor = mongo_collection.find(query, projection).limit(sample_size)
    
    # Process each document
    for doc in cursor:
        for field, value in doc.items():
            # Record field name
            analysis["fields"][field].add(True)
            
            # Record value type
            value_type = type(value).__name__
            analysis["field_types"][field].add(value_type)
            
            # Special handling for specific field types
            if field not in analysis["field_stats"]:
                analysis["field_stats"][field] = {
                    "count": 0,
                    "missing": 0,
                    "unique_values": set(),
                }
            
            analysis["field_stats"][field]["count"] += 1
            
            # Track unique values for categorical fields (with reasonable cardinality)
            if isinstance(value, (str, int, bool)) and len(str(value)) < 100:
                analysis["field_stats"][field]["unique_values"].add(value)
    
    # Calculate missing values
    for field in analysis["fields"]:
        analysis["field_stats"][field]["missing"] = sample_size - analysis["field_stats"][field]["count"]
        analysis["field_stats"][field]["unique_count"] = len(analysis["field_stats"][field]["unique_values"])
        
        # Convert sets to lists for JSON serialization
        if len(analysis["field_stats"][field]["unique_values"]) <= 20:
            analysis["field_stats"][field]["unique_values"] = list(analysis["field_stats"][field]["unique_values"])
        else:
            # Too many values to display, just show count
            analysis["field_stats"][field]["unique_values"] = f"[{analysis['field_stats'][field]['unique_count']} unique values]"
    
    # Convert sets to lists for JSON serialization
    analysis["fields"] = {k: True for k in analysis["fields"].keys()}
    analysis["field_types"] = {k: list(v) for k, v in analysis["field_types"].items()}
    
    return analysis

# Data Reporting Utilities
def generate_date_distribution_report(date_counts, title="Date Distribution Report"):
    """
    Generate a formatted report of date-based paper distribution.
    
    Args:
        date_counts: OrderedDict of dates and counts
        title: Report title
        
    Returns:
        Formatted report string
    """
    if not date_counts:
        return "No data available for reporting."
    
    total = sum(date_counts.values())
    max_count = max(date_counts.values()) if date_counts else 0
    scale_factor = 40 / max_count if max_count > 0 else 0
    
    # Generate the report
    lines = []
    lines.append(f"📊 {title} 📊")
    lines.append("-" * 60)
    
    # Determine header based on the first key format
    if date_counts:
        first_key = next(iter(date_counts.keys()))
        if len(first_key) == 4:  # Year
            lines.append(f"{'Year':<6} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<40}")
        elif len(first_key) == 7:  # Year-Month
            lines.append(f"{'Year-Month':<10} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<40}")
        elif len(first_key) == 10:  # Full date
            lines.append(f"{'Date':<10} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<40}")
        else:  # Weekday or other
            lines.append(f"{'Period':<10} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<40}")
    
    lines.append("-" * 60)
    
    # Add data rows
    for date, count in date_counts.items():
        percentage = (count / total) * 100 if total > 0 else 0
        bar_length = int(count * scale_factor)
        bar = "█" * bar_length
        
        if len(date) == 4:  # Year
            lines.append(f"{date:<6} | {count:>8,d} | {percentage:>10.2f}% | {bar}")
        else:  # Other formats
            lines.append(f"{date:<10} | {count:>8,d} | {percentage:>10.2f}% | {bar}")
    
    lines.append("-" * 60)
    lines.append(f"Total: {total:,d} papers")
    
    return "\n".join(lines)

# MongoDB Validation and Reporting
def validate_mongodb_data(mongo_collection, validation_func, sample_size=100):
    """
    Validate a sample of documents in a MongoDB collection.
    
    Args:
        mongo_collection: MongoDB collection object
        validation_func: Function that validates a document and returns (bool, [errors])
        sample_size: Number of documents to validate
        
    Returns:
        Dictionary with validation results
    """
    total_count = mongo_collection.count_documents({})
    if total_count == 0:
        return {
            "total_documents": 0,
            "validated_documents": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "error_summary": {},
            "sample_errors": []
        }
    
    # Adjust sample size if collection has fewer documents
    sample_size = min(sample_size, total_count)
    
    # Get random sample of documents
    pipeline = [
        {"$sample": {"size": sample_size}}
    ]
    documents = list(mongo_collection.aggregate(pipeline))
    
    valid_count = 0
    invalid_count = 0
    error_types = defaultdict(int)
    sample_errors = []
    
    # Validate each document
    for doc in documents:
        is_valid, errors = validation_func(doc)
        
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            for error in errors:
                error_types[error] += 1
            
            # Store sample of invalid documents with their errors
            if len(sample_errors) < 10:  # Limit to 10 samples
                doc_id = str(doc.get("_id", "")) if "_id" in doc else "unknown"
                sample_errors.append({
                    "document_id": doc_id,
                    "errors": errors
                })
    
    return {
        "total_documents": total_count,
        "validated_documents": sample_size,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "error_summary": dict(error_types),
        "sample_errors": sample_errors
    }

# Data Integrity Checking
def check_data_integrity(mongo_collection, date_range=None):
    """
    Check data integrity with focus on temporal consistency.
    
    Args:
        mongo_collection: MongoDB collection to check
        date_range: Optional tuple of (start_date, end_date) strings
        
    Returns:
        Dictionary with integrity check results
    """
    results = {
        "total_documents": mongo_collection.count_documents({}),
        "integrity_checks": {}
    }
    
    # Query filter
    query = {}
    if date_range:
        start_date, end_date = date_range
        query["published"] = {
            "$gte": start_date,
            "$lte": end_date
        }
    
    # Check for duplicate IDs
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "duplicate_count"}
    ]
    duplicate_result = list(mongo_collection.aggregate(pipeline))
    results["integrity_checks"]["duplicate_ids"] = duplicate_result[0]["duplicate_count"] if duplicate_result else 0
    
    # Check for missing required fields
    required_fields = ["id", "title", "published", "authors", "categories"]
    for field in required_fields:
        field_query = query.copy()
        field_query[field] = {"$exists": False}
        results["integrity_checks"][f"missing_{field}"] = mongo_collection.count_documents(field_query)
    
    # Check for temporal anomalies (future dates)
    future_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    future_query = query.copy()
    future_query["published"] = {"$gt": future_date}
    results["integrity_checks"]["future_dates"] = mongo_collection.count_documents(future_query)
    
    # Data completeness by time period
    if date_range:
        # Check for time gaps in the data
        monthly_counts = count_papers_by_date(mongo_collection, "published", "month")
        
        # Convert month strings to datetime for gap analysis
        months = [(datetime.strptime(m, "%Y-%m"), count) for m, count in monthly_counts.items()]
        months.sort(key=lambda x: x[0])
        
        # Find gaps (months with zero papers)
        gaps = []
        for i in range(len(months) - 1):
            current_month = months[i][0]
            next_month = months[i + 1][0]
            
            # Calculate expected next month
            expected_next = current_month.replace(day=1)
            if current_month.month == 12:
                expected_next = expected_next.replace(year=current_month.year + 1, month=1)
            else:
                expected_next = expected_next.replace(month=current_month.month + 1)
            
            # Check if there's a gap
            if expected_next < next_month:
                gap_months = []
                gap_date = expected_next
                while gap_date < next_month:
                    gap_months.append(gap_date.strftime("%Y-%m"))
                    if gap_date.month == 12:
                        gap_date = gap_date.replace(year=gap_date.year + 1, month=1)
                    else:
                        gap_date = gap_date.replace(month=gap_date.month + 1)
                
                gaps.append(gap_months)
        
        results["integrity_checks"]["time_gaps"] = gaps
    
    return results