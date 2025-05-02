from neo4j import GraphDatabase
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Neo4jSync:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def sync_papers(self, papers: List[Dict[str, Any]]):
        with self.driver.session() as session:
            for paper in papers:
                session.write_transaction(self._create_paper, paper)
                for author in paper.get('authors', []):
                    session.write_transaction(self._create_author_and_relationship, paper['id'], author)
                for category in paper.get('categories', []):
                    session.write_transaction(self._create_category_and_relationship, paper['id'], category)

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