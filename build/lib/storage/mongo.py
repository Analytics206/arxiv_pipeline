import pymongo
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MongoStorage:
    """MongoDB storage for arXiv papers."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers"
    ):
        """
        Initialize MongoDB connection.

        Args:
            connection_string: MongoDB connection URI
            db_name: Target database name
        """
        self.client = pymongo.MongoClient(connection_string)
        self.db = self.client[db_name]
        self.papers = self.db.papers
        self.stats = self.db.ingestion_stats

        # Create indexes
        self._setup_indexes()

    def _setup_indexes(self):
        """Set up MongoDB indexes for optimized queries."""
        self.papers.create_index("id", unique=True)
        self.papers.create_index("categories")
        self.papers.create_index("authors")
        self.papers.create_index("published")
        logger.info("MongoDB indexes initialized")

    def store_papers(self, papers: List[Dict]) -> Dict[str, int]:
        """
        Store papers in MongoDB with upsert to handle duplicates.

        Args:
            papers: List of paper metadata dictionaries

        Returns:
            Stats dictionary with counts of inserted and updated documents
        """
        from pymongo.errors import PyMongoError

        inserted = 0
        updated = 0
        failed = 0

        for paper in papers:
            try:
                paper['ingestion_timestamp'] = datetime.utcnow()
                result = self.papers.update_one(
                    {"id": paper["id"]},
                    {"$set": paper},
                    upsert=True
                )
                if result.upserted_id:
                    inserted += 1
                elif result.modified_count > 0:
                    updated += 1
            except PyMongoError as e:
                logger.error(f"MongoDB error storing paper {paper.get('id', 'unknown')}: {str(e)}")
                failed += 1
            except Exception as e:
                logger.exception(f"Unexpected error storing paper {paper.get('id', 'unknown')}: {str(e)}")
                failed += 1

        stats = {
            "timestamp": datetime.utcnow(),
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "total_processed": len(papers)
        }

        try:
            self.stats.insert_one(stats)
        except PyMongoError as e:
            logger.warning(f"Could not log ingestion stats: {str(e)}")

        logger.info(f"Stored {inserted} new papers, updated {updated}, failed {failed}")
        return stats

    def store_papers_bulk(self, papers: List[Dict]) -> Dict[str, int]:
        """
        Bulk upsert papers for efficiency with large batches.

        Args:
            papers: List of paper metadata dictionaries

        Returns:
            Stats dictionary with counts of inserted and updated documents
        """
        from pymongo import UpdateOne
        from pymongo.errors import BulkWriteError, PyMongoError

        operations = []
        for paper in papers:
            paper['ingestion_timestamp'] = datetime.utcnow()
            operations.append(
                UpdateOne({"id": paper["id"]}, {"$set": paper}, upsert=True)
            )

        inserted = 0
        updated = 0
        failed = 0

        if not operations:
            return {"inserted": 0, "updated": 0, "failed": 0, "total_processed": 0}

        try:
            result = self.papers.bulk_write(operations, ordered=False)
            inserted = result.upserted_count
            updated = result.modified_count
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error: {bwe.details}")
            failed = len(papers) - (inserted + updated)
        except PyMongoError as e:
            logger.error(f"MongoDB error during bulk write: {str(e)}")
            failed = len(papers)
        except Exception as e:
            logger.exception(f"Unexpected error during bulk write: {str(e)}")
            failed = len(papers)

        stats = {
            "timestamp": datetime.utcnow(),
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "total_processed": len(papers)
        }

        try:
            self.stats.insert_one(stats)
        except PyMongoError as e:
            logger.warning(f"Could not log ingestion stats: {str(e)}")

        logger.info(f"Bulk stored {inserted} new papers, updated {updated}, failed {failed}")
        return stats

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """Retrieve single paper by ID."""
        return self.papers.find_one({"id": paper_id})

    def get_papers(
        self,
        filter_query: Dict = None,
        limit: int = 100,
        skip: int = 0,
        sort_by: str = "published",
        sort_order: int = -1
    ) -> List[Dict]:
        """
        Retrieve papers with filtering, pagination and sorting.

        Args:
            filter_query: MongoDB filter query
            limit: Max number of results
            skip: Number of documents to skip (pagination)
            sort_by: Field to sort by
            sort_order: pymongo.ASCENDING (1) or pymongo.DESCENDING (-1)

        Returns:
            List of paper documents
        """
        if filter_query is None:
            filter_query = {}

        cursor = self.papers.find(filter_query)
        cursor = cursor.sort(sort_by, sort_order).skip(skip).limit(limit)

        return list(cursor)

    def get_stats(self, limit: int = 10) -> List[Dict]:
        """Get recent ingestion statistics."""
        return list(self.stats.find().sort("timestamp", -1).limit(limit))

    def close(self):
        """Close MongoDB connection."""
        self.client.close()

    def __enter__(self):
        """Enable use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure connection is closed when exiting context."""
        self.close()