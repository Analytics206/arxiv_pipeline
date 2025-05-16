from neo4j import GraphDatabase
from typing import List, Dict, Any, Tuple
import logging
import time

logger = logging.getLogger(__name__)

class Neo4jSync:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Test connection
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        if self.driver:
            self.driver.close()
    
    def clear_database(self):
        """Clear all data from the Neo4j database"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Neo4j database has been cleared")
    
    def sync_papers(self, papers: List[Dict[str, Any]]):
        """Legacy method for backward compatibility"""
        success, errors = self.sync_papers_batch(papers)
        return success

    def sync_papers_batch(self, papers: List[Dict[str, Any]], sync_timestamp: str = None) -> Tuple[int, int]:
        """Sync a batch of papers to Neo4j using optimized batch operations
        
        Args:
            papers: List of paper documents from MongoDB
            sync_timestamp: Optional timestamp to mark this sync operation
            
        Returns:
            Tuple of (success_count, error_count)
        """
        success_count = 0
        error_count = 0
        batch_start_time = time.time()
        
        try:
            with self.driver.session() as session:
                # Process papers in a single transaction per batch
                for idx, paper in enumerate(papers):
                    try:
                        # Create paper
                        session.write_transaction(self._create_paper, paper)
                        
                        # Create authors in batch
                        if paper.get('authors', []):
                            authors_batch = [(paper['id'], author) for author in paper.get('authors', [])]
                            session.write_transaction(self._create_authors_batch, authors_batch)
                        
                        # Create categories in batch
                        if paper.get('categories', []):
                            categories_batch = [(paper['id'], category) for category in paper.get('categories', [])]
                            session.write_transaction(self._create_categories_batch, categories_batch)
                        
                        # Mark paper with sync timestamp if provided
                        if sync_timestamp:
                            session.write_transaction(
                                self._mark_paper_synced, paper['id'], sync_timestamp
                            )
                            
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        paper_id = paper.get('id', 'unknown')
                        logger.error(f"Failed to sync paper {paper_id}: {e}")
                        
                        # Don't let one paper failure crash the entire batch
                        continue
        
        except Exception as e:
            logger.error(f"Failed to process batch: {e}")
            error_count += len(papers) - success_count
        
        batch_time = time.time() - batch_start_time
        papers_per_second = len(papers) / batch_time if batch_time > 0 else 0
        logger.info(f"Batch processed in {batch_time:.2f} seconds ({papers_per_second:.2f} papers/sec)")
        
        return success_count, error_count

    @staticmethod
    def _create_paper(tx, paper: Dict[str, Any]):
        tx.run(
            """
            MERGE (p:Paper {id: $id})
            SET p.title = $title,
                p.summary = $summary,
                p.published = $published,
                p.updated = $updated,
                p.arxiv_url = $arxiv_url,
                p.pdf_url = $pdf_url
            """,
            id=paper.get('id', ''),
            title=paper.get('title', ''),
            summary=paper.get('summary', ''),
            published=paper.get('published', ''),
            updated=paper.get('updated', ''),
            arxiv_url=paper.get('arxiv_url', ''),
            pdf_url=paper.get('pdf_url', '')
        )

    @staticmethod
    def _create_author_and_relationship(tx, paper_id: str, author_name: str):
        tx.run(
            """
            MERGE (a:Author {name: $author_name})
            MERGE (p:Paper {id: $paper_id})
            MERGE (a)-[:AUTHORED]->(p)
            """,
            author_name=author_name,
            paper_id=paper_id
        )
        
    @staticmethod
    def _create_authors_batch(tx, authors_data: List[Tuple[str, str]]):
        """Create multiple authors and their relationships to papers in a single transaction
        
        Args:
            authors_data: List of (paper_id, author_name) tuples
        """
        # Use UNWIND for batch processing
        tx.run(
            """
            UNWIND $authors_data AS author_data
            MERGE (a:Author {name: author_data[1]})
            MERGE (p:Paper {id: author_data[0]})
            MERGE (a)-[:AUTHORED]->(p)
            """,
            authors_data=authors_data
        )

    @staticmethod
    def _create_category_and_relationship(tx, paper_id: str, category: str):
        tx.run(
            """
            MERGE (c:Category {name: $category})
            MERGE (p:Paper {id: $paper_id})
            MERGE (p)-[:IN_CATEGORY]->(c)
            """,
            category=category,
            paper_id=paper_id
        )
    
    @staticmethod
    def _create_categories_batch(tx, categories_data: List[Tuple[str, str]]):
        """Create multiple categories and their relationships to papers in a single transaction
        
        Args:
            categories_data: List of (paper_id, category) tuples
        """
        # Use UNWIND for batch processing
        tx.run(
            """
            UNWIND $categories_data AS category_data
            MERGE (c:Category {name: category_data[1]})
            MERGE (p:Paper {id: category_data[0]})
            MERGE (p)-[:IN_CATEGORY]->(c)
            """,
            categories_data=categories_data
        )
    
    @staticmethod
    def _mark_paper_synced(tx, paper_id: str, timestamp: str):
        """Mark a paper as synced with the given timestamp
        
        Args:
            paper_id: ID of the paper
            timestamp: ISO format timestamp string
        """
        tx.run(
            """
            MATCH (p:Paper {id: $paper_id})
            SET p.last_synced = $timestamp
            """,
            paper_id=paper_id,
            timestamp=timestamp
        )