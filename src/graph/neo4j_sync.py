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
                session.write_transaction(self._create_paper_with_authors_and_categories, paper)

    @staticmethod
    def _create_paper_with_authors_and_categories(tx, paper: Dict[str, Any]):
        tx.run(
            """
            MERGE (p:Paper {id: $id})
            SET p.title = $title, p.summary = $summary, p.published = $published, p.updated = $updated, p.arxiv_url = $arxiv_url, p.pdf_url = $pdf_url
            """,
            id=paper['id'],
            title=paper.get('title', ''),
            summary=paper.get('summary', ''),
            published=paper.get('published', ''),
            updated=paper.get('updated', ''),
            arxiv_url=paper.get('arxiv_url', ''),
            pdf_url=paper.get('pdf_url', '')
        )
        for author in paper.get('authors', []):
            tx.run(
                """
                MERGE (a:Author {name: $name})
                MERGE (p:Paper {id: $paper_id})
                MERGE (a)-[:AUTHORED]->(p)
                """,
                name=author,
                paper_id=paper['id']
            )
        for category in paper.get('categories', []):
            tx.run(
                """
                MERGE (c:Category {name: $cat})
                MERGE (p:Paper {id: $paper_id})
                MERGE (p)-[:IN_CATEGORY]->(c)
                """,
                cat=category,
                paper_id=paper['id']
            )