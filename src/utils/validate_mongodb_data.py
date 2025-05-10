"""
ArXiv Papers MongoDB Data Validation Tool

This script demonstrates the use of the data validation and analysis 
utilities in the ArXiv Pipeline. It performs validation and analysis
on the papers collection in MongoDB and generates reports.
"""

import os
import sys
import json
from datetime import datetime
import argparse

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import utilities from the project
from src.agents_core.logging_utils import (
    setup_logger,
    validate_paper_schema,
    count_papers_by_date,
    analyze_mongodb_collection,
    validate_mongodb_data,
    check_data_integrity,
    generate_date_distribution_report
)
from src.storage.mongo import MongoStorage

# Configure logging
logger = setup_logger('mongodb_validator', 'INFO')

def run_validation(connection_string=None, db_name=None, sample_size=100, date_range=None):
    """
    Run comprehensive data validation and analysis on the MongoDB papers collection.
    
    Args:
        connection_string: MongoDB connection URI (if None, uses MONGO_URI env var or default)
        db_name: MongoDB database name (if None, uses MONGO_DB env var or default)
        sample_size: Number of documents to validate
        date_range: Optional tuple of (start_date, end_date) strings
    """
    # Use environment variables or default values
    if connection_string is None:
        connection_string = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    
    if db_name is None:
        db_name = os.environ.get("MONGO_DB", "arxiv_papers")
    
    logger.info(f"Connecting to MongoDB at {connection_string}, database: {db_name}")
    
    # Connect to MongoDB
    with MongoStorage(connection_string=connection_string, db_name=db_name) as mongo:
        papers_collection = mongo.papers
        
        # =======================================================
        # 1. Basic collection analysis
        # =======================================================
        logger.info("Analyzing MongoDB papers collection structure...")
        analysis = analyze_mongodb_collection(papers_collection)
        
        print("\n" + "="*80)
        print(f"📊 MONGODB COLLECTION ANALYSIS: {analysis['collection_name']} 📊")
        print("="*80)
        print(f"Total documents: {analysis['document_count']:,}")
        print(f"Fields found: {', '.join(sorted(analysis['fields'].keys()))}")
        
        # Print field type information
        print("\nField Types:")
        for field, types in sorted(analysis['field_types'].items()):
            type_str = ", ".join(types)
            print(f"  - {field}: {type_str}")
        
        # =======================================================
        # 2. Schema validation
        # =======================================================
        logger.info(f"Validating paper schema for {sample_size} random documents...")
        validation_results = validate_mongodb_data(
            papers_collection, 
            validate_paper_schema,
            sample_size=sample_size
        )
        
        print("\n" + "="*80)
        print("🔍 SCHEMA VALIDATION RESULTS 🔍")
        print("="*80)
        print(f"Total documents: {validation_results['total_documents']:,}")
        print(f"Documents validated: {validation_results['validated_documents']:,}")
        print(f"Valid documents: {validation_results['valid_count']:,}")
        print(f"Invalid documents: {validation_results['invalid_count']:,}")
        
        if validation_results['invalid_count'] > 0:
            print("\nError Summary:")
            for error, count in validation_results['error_summary'].items():
                print(f"  - {error}: {count} occurrences")
            
            if validation_results['sample_errors']:
                print("\nSample Error Details:")
                for i, sample in enumerate(validation_results['sample_errors'][:3], 1):
                    print(f"  Document #{i} (ID: {sample['document_id']}):")
                    for error in sample['errors']:
                        print(f"    - {error}")
        
        # =======================================================
        # 3. Temporal analysis
        # =======================================================
        logger.info("Analyzing paper publication dates...")
        
        # Publication by year
        yearly_counts = count_papers_by_date(papers_collection, "published", "year")
        print("\n" + generate_date_distribution_report(yearly_counts, "Papers by Year"))
        
        # Publication by month (last 24 months)
        monthly_counts = count_papers_by_date(papers_collection, "published", "month")
        recent_months = dict(list(monthly_counts.items())[-24:]) if len(monthly_counts) > 24 else monthly_counts
        print("\n" + generate_date_distribution_report(recent_months, "Papers by Month (Last 24 Months)"))
        
        # Publication by day of week
        weekday_counts = count_papers_by_date(papers_collection, "published", "weekday")
        print("\n" + generate_date_distribution_report(weekday_counts, "Papers by Day of Week"))
        
        # =======================================================
        # 4. Data integrity check
        # =======================================================
        logger.info("Checking data integrity...")
        integrity_check = check_data_integrity(papers_collection, date_range)
        
        print("\n" + "="*80)
        print("🛡️ DATA INTEGRITY CHECK 🛡️")
        print("="*80)
        
        # Print integrity check results
        print(f"Total documents checked: {integrity_check['total_documents']:,}")
        
        integrity_checks = integrity_check['integrity_checks']
        print("\nIntegrity Issues:")
        print(f"  - Duplicate IDs: {integrity_checks.get('duplicate_ids', 0):,}")
        print(f"  - Missing title field: {integrity_checks.get('missing_title', 0):,}")
        print(f"  - Missing authors field: {integrity_checks.get('missing_authors', 0):,}")
        print(f"  - Missing categories field: {integrity_checks.get('missing_categories', 0):,}")
        print(f"  - Missing published field: {integrity_checks.get('missing_published', 0):,}")
        print(f"  - Future dates: {integrity_checks.get('future_dates', 0):,}")
        
        if 'time_gaps' in integrity_checks and integrity_checks['time_gaps']:
            print("\nTime gaps found (months with no papers):")
            for i, gap in enumerate(integrity_checks['time_gaps'], 1):
                print(f"  Gap #{i}: {', '.join(gap)}")
        
        print("\n" + "="*80)
        print("✅ VALIDATION COMPLETE ✅")
        print("="*80)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Validate and analyze ArXiv papers data in MongoDB"
    )
    parser.add_argument(
        "--connection", 
        help="MongoDB connection string (default: uses MONGO_URI environment variable or localhost)"
    )
    parser.add_argument(
        "--db", 
        help="MongoDB database name (default: uses MONGO_DB environment variable or 'arxiv_papers')"
    )
    parser.add_argument(
        "--sample", 
        type=int, 
        default=100,
        help="Number of documents to validate (default: 100)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date for data integrity check (format: YYYY-MM-DDThh:mm:ssZ)"
    )
    parser.add_argument(
        "--end-date",
        help="End date for data integrity check (format: YYYY-MM-DDThh:mm:ssZ)"
    )
    
    args = parser.parse_args()
    
    # Set up date range if provided
    date_range = None
    if args.start_date and args.end_date:
        date_range = (args.start_date, args.end_date)
    
    # Run validation
    run_validation(
        connection_string=args.connection,
        db_name=args.db,
        sample_size=args.sample,
        date_range=date_range
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
