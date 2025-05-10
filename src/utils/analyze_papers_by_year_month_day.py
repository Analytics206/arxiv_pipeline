"""
Analyze ArXiv papers by year, month, and day from MongoDB.
This utility script provides a hierarchical analysis of paper publication 
dates organized by year, month, and day.
"""

import os
import sys
import logging
from datetime import datetime
from collections import OrderedDict, defaultdict
import argparse

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the MongoStorage class from the project
from src.storage.mongo import MongoStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_papers_by_year_month_day(connection_string=None, db_name="arxiv_papers", 
                                    start_date=None, end_date=None, year_filter=None, category=None):
    """
    Query MongoDB and analyze papers hierarchically by year, month, and day.
    
    Args:
        connection_string: MongoDB connection URI (if None, uses MONGO_URI env var or default)
        db_name: MongoDB database name
        start_date: Optional start date filter (format: YYYY-MM-DD)
        end_date: Optional end date filter (format: YYYY-MM-DD)
        year_filter: Optional year to filter results (e.g., 2024)
        category: Optional category filter (e.g., 'cs.AI' or 'math.ST')
        
    Returns:
        Tuple of (yearly_data, monthly_data, daily_data, total_papers, categories_list)
    """
    # Use environment variable or default connection string
    if connection_string is None:
        connection_string = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    
    logger.info(f"Connecting to MongoDB at {connection_string}")
    
    # Prepare filter query
    filter_query = {}
    if start_date:
        filter_query["published"] = {"$gte": f"{start_date}T00:00:00Z"}
    if end_date:
        if "published" not in filter_query:
            filter_query["published"] = {}
        filter_query["published"]["$lte"] = f"{end_date}T23:59:59Z"
    
    # Add category filter if specified
    if category:
        filter_query["categories"] = {"$in": [category]}
        logger.info(f"Filtering by category: {category}")
    
    try:
        # Connect to MongoDB using the project's MongoStorage class
        with MongoStorage(connection_string=connection_string, db_name=db_name) as mongo:
            # Get total paper count
            total_papers = mongo.papers.count_documents(filter_query)
            logger.info(f"Total papers matching filter: {total_papers}")
            
            # Query to extract year, month, and day from the published field
            pipeline = [
                {"$match": filter_query},
                {"$addFields": {
                    "year": {"$substr": ["$published", 0, 4]},
                    "month": {"$substr": ["$published", 5, 2]},
                    "day": {"$substr": ["$published", 8, 2]},
                    "yearMonth": {"$substr": ["$published", 0, 7]},
                    "fullDate": {"$substr": ["$published", 0, 10]}
                }},
                {"$sort": {"published": 1}}  # Sort by date ascending
            ]
            
            # Apply year filter if specified
            if year_filter:
                pipeline[0]["$match"]["published"] = pipeline[0]["$match"].get("published", {})
                pipeline[0]["$match"]["published"]["$regex"] = f"^{year_filter}"
            
            # Execute the query
            logger.info("Executing aggregation query...")
            cursor = mongo.papers.aggregate(pipeline)
            
            # Process results into hierarchical structure
            yearly_data = defaultdict(int)
            monthly_data = defaultdict(int)
            daily_data = defaultdict(int)
            
            # Get all unique categories for dropdown (limit to most common)
            categories_pipeline = [
                {"$unwind": "$categories"},
                {"$group": {"_id": "$categories", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 50}  # Get top 50 categories
            ]
            categories_cursor = mongo.papers.aggregate(categories_pipeline)
            categories_list = [doc["_id"] for doc in categories_cursor]
            
            # Process each document
            for doc in cursor:
                year = doc.get("year")
                month = doc.get("month")
                day = doc.get("day")
                year_month = doc.get("yearMonth")
                full_date = doc.get("fullDate")
                
                yearly_data[year] += 1
                monthly_data[year_month] += 1
                daily_data[full_date] += 1
            
            # Convert to ordered dictionaries
            yearly_data = OrderedDict(sorted(yearly_data.items()))
            monthly_data = OrderedDict(sorted(monthly_data.items()))
            daily_data = OrderedDict(sorted(daily_data.items()))
            
            return yearly_data, monthly_data, daily_data, total_papers, categories_list
            
    except Exception as e:
        logger.error(f"Error querying MongoDB: {str(e)}")
        return OrderedDict(), OrderedDict(), OrderedDict(), 0, []

def display_yearly_summary(yearly_data, total_papers):
    """Display paper counts by year with visualization."""
    if not yearly_data:
        print("No yearly data available.")
        return
        
    print("\n📊 ArXiv Papers by Year 📊")
    print("-" * 50)
    print(f"{'Year':<6} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<20}")
    print("-" * 50)
    
    max_count = max(yearly_data.values())
    scale_factor = 20 / max_count if max_count > 0 else 0
    
    for year, count in yearly_data.items():
        percentage = (count / total_papers) * 100 if total_papers > 0 else 0
        bar_length = int(count * scale_factor)
        bar = "█" * bar_length
        print(f"{year:<6} | {count:>8,d} | {percentage:>10.2f}% | {bar}")
    
    print("-" * 50)

def display_monthly_summary(monthly_data, total_papers, year_filter=None):
    """Display paper counts by year-month with visualization."""
    if not monthly_data:
        print("No monthly data available.")
        return
    
    filtered_data = OrderedDict()
    for year_month, count in monthly_data.items():
        if year_filter and not year_month.startswith(year_filter):
            continue
        filtered_data[year_month] = count
    
    if not filtered_data:
        print(f"No monthly data available for year {year_filter}.")
        return
        
    year_heading = f" for {year_filter}" if year_filter else ""
    print(f"\n📅 ArXiv Papers by Month{year_heading} 📅")
    print("-" * 60)
    print(f"{'Year-Month':<10} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<25}")
    print("-" * 60)
    
    max_count = max(filtered_data.values())
    scale_factor = 25 / max_count if max_count > 0 else 0
    
    for year_month, count in filtered_data.items():
        percentage = (count / total_papers) * 100 if total_papers > 0 else 0
        bar_length = int(count * scale_factor)
        bar = "█" * bar_length
        print(f"{year_month:<10} | {count:>8,d} | {percentage:>10.2f}% | {bar}")
    
    print("-" * 60)

def display_daily_summary(daily_data, total_papers, year_month_filter=None, max_days=31):
    """Display paper counts by full date with visualization."""
    if not daily_data:
        print("No daily data available.")
        return
    
    filtered_data = OrderedDict()
    for date, count in daily_data.items():
        if year_month_filter and not date.startswith(year_month_filter):
            continue
        filtered_data[date] = count
    
    # Limit to the specified number of days
    if len(filtered_data) > max_days:
        filtered_data = OrderedDict(list(filtered_data.items())[-max_days:])
    
    if not filtered_data:
        print(f"No daily data available for the filter {year_month_filter}.")
        return
        
    filter_heading = f" for {year_month_filter}" if year_month_filter else " (Last {max_days} Days)"
    print(f"\n📆 ArXiv Papers by Day{filter_heading} 📆")
    print("-" * 60)
    print(f"{'Date':<10} | {'Count':>6} | {'Percentage':>8} | {'Day of Week':^10} | {'Distribution':<15}")
    print("-" * 60)
    
    max_count = max(filtered_data.values())
    scale_factor = 15 / max_count if max_count > 0 else 0
    
    for date, count in filtered_data.items():
        percentage = (count / total_papers) * 100 if total_papers > 0 else 0
        
        # Calculate day of week
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_of_week = date_obj.strftime("%A")
        except:
            day_of_week = "Unknown"
            
        bar_length = int(count * scale_factor)
        bar = "█" * bar_length
        print(f"{date:<10} | {count:>6,d} | {percentage:>7.2f}% | {day_of_week:^10} | {bar}")
    
    print("-" * 60)

def calculate_day_of_week_stats(daily_data):
    """Calculate paper counts by day of week."""
    day_of_week_counts = defaultdict(int)
    day_names = {
        0: "Monday",
        1: "Tuesday", 
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }
    
    for date, count in daily_data.items():
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            weekday = date_obj.weekday()  # 0 = Monday, 6 = Sunday
            day_of_week_counts[weekday] += count
        except:
            continue
    
    # Convert to ordered dict by day of week
    result = OrderedDict()
    for i in range(7):
        result[day_names[i]] = day_of_week_counts[i]
    
    return result

def display_day_of_week_stats(day_of_week_data, total_papers):
    """Display paper counts by day of week with visualization."""
    if not day_of_week_data:
        print("No day of week data available.")
        return
        
    print("\n📊 ArXiv Papers by Day of Week 📊")
    print("-" * 60)
    print(f"{'Day':^10} | {'Count':>8} | {'Percentage':>11} | {'Distribution':<25}")
    print("-" * 60)
    
    max_count = max(day_of_week_data.values())
    scale_factor = 25 / max_count if max_count > 0 else 0
    
    for day, count in day_of_week_data.items():
        percentage = (count / total_papers) * 100 if total_papers > 0 else 0
        bar_length = int(count * scale_factor)
        bar = "█" * bar_length
        print(f"{day:^10} | {count:>8,d} | {percentage:>10.2f}% | {bar}")
    
    print("-" * 60)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Analyze ArXiv papers by year, month, and day")
    parser.add_argument("--start-date", help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date filter (YYYY-MM-DD)")
    parser.add_argument("--year", help="Filter by specific year (YYYY)")
    parser.add_argument("--month", help="Filter by specific month (YYYY-MM)")
    parser.add_argument("--connection", help="MongoDB connection string")
    parser.add_argument("--db", help="MongoDB database name")
    args = parser.parse_args()
    
    try:
        # Get MongoDB connection string from environment variable or argument
        mongo_uri = args.connection or os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        db_name = args.db or os.environ.get("MONGO_DB", "arxiv_papers")
        
        # Get data
        yearly_data, monthly_data, daily_data, total_papers = analyze_papers_by_year_month_day(
            connection_string=mongo_uri,
            db_name=db_name,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        if total_papers == 0:
            print("No papers found matching the criteria.")
            return 1
            
        # Display hierarchical summaries
        display_yearly_summary(yearly_data, total_papers)
        
        # If year filter is provided, show only months for that year
        display_monthly_summary(monthly_data, total_papers, args.year)
        
        # If month filter is provided, show daily breakdown for that month
        display_daily_summary(daily_data, total_papers, args.month)
        
        # Calculate and display day of week statistics
        day_of_week_stats = calculate_day_of_week_stats(daily_data)
        display_day_of_week_stats(day_of_week_stats, total_papers)
        
        # Print summary
        print(f"\nTotal Papers: {total_papers:,d}")
        print(f"Distinct Years: {len(yearly_data)}")
        print(f"Distinct Months: {len(monthly_data)}")
        print(f"Distinct Days: {len(daily_data)}")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
