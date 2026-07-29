import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pymongo

from src.analysis.identity import paper_lookup_aliases
from src.ingestion.schema import (
    canonicalize_paper_metadata,
    paper_identity_from_metadata,
    paper_version_sort_key,
)
from src.storage.paper_archive import (
    PAPERS_ARCHIVE_COLLECTION,
    build_paper_cleanup_plan,
)

logger = logging.getLogger(__name__)


class MongoStorage:
    """MongoDB storage for arXiv papers."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers",
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
        self.paper_archive = self.db[PAPERS_ARCHIVE_COLLECTION]
        self.stats = self.db.ingestion_stats

        # Create indexes
        self._setup_indexes()

    def _setup_indexes(self):
        """Set up MongoDB indexes for optimized queries."""
        from pymongo.errors import DuplicateKeyError, OperationFailure

        self.papers.create_index("id", unique=True)
        self.papers.create_index("categories")
        self.papers.create_index("authors")
        self.papers.create_index("published")
        try:
            self.papers.create_index(
                "base_arxiv_id",
                name="base_arxiv_id_unique",
                unique=True,
                partialFilterExpression={"base_arxiv_id": {"$type": "string"}},
            )
        except (DuplicateKeyError, OperationFailure) as error:
            if getattr(error, "code", None) != 11000:
                raise
            logger.warning(
                "Deferring the unique base_arxiv_id index until paper "
                "version cleanup removes existing duplicates"
            )
        self.paper_archive.create_index(
            [("base_arxiv_id", 1), ("arxiv_version", 1)],
            name="archived_paper_version_unique",
            unique=True,
        )
        self.paper_archive.create_index("archived_at")
        logger.info("MongoDB indexes initialized")

    def store_papers(self, papers: List[Dict]) -> Dict[str, int]:
        """Store papers using the same version-aware path as bulk imports."""

        return self.store_papers_bulk(papers)

    def store_papers_bulk(self, papers: List[Dict]) -> Dict[str, int]:
        """
        Bulk upsert papers for efficiency with large batches.

        Args:
            papers: List of paper metadata dictionaries

        Returns:
            Stats dictionary with counts of inserted and updated documents
        """
        from pymongo import ReplaceOne, UpdateOne
        from pymongo.errors import BulkWriteError, PyMongoError

        now = datetime.now(timezone.utc)
        canonical_by_base: dict[str, dict[str, Any]] = {}
        invalid = 0
        for paper in papers:
            try:
                canonical = canonicalize_paper_metadata(paper)
            except ValueError as error:
                logger.error("Skipping paper with invalid identity: %s", error)
                invalid += 1
                continue
            canonical["ingestion_timestamp"] = now
            base_id = canonical["base_arxiv_id"]
            previous = canonical_by_base.get(base_id)
            if previous is None or paper_version_sort_key(
                canonical
            ) > paper_version_sort_key(previous):
                canonical_by_base[base_id] = canonical

        inserted = 0
        updated = 0
        archived = 0
        skipped_older = 0
        failed = invalid

        if not canonical_by_base:
            return {
                "inserted": 0,
                "updated": 0,
                "archived": 0,
                "skipped_older": 0,
                "failed": failed,
                "total_processed": len(papers),
            }

        base_ids = list(canonical_by_base)
        aliases = [
            alias
            for paper in canonical_by_base.values()
            for alias in paper_lookup_aliases(paper["arxiv_id"])
        ]
        existing_documents = list(
            self.papers.find(
                {
                    "$or": [
                        {"base_arxiv_id": {"$in": base_ids}},
                        {"id": {"$in": aliases}},
                    ]
                }
            )
        )
        existing_by_base: dict[str, dict[str, Any]] = {}
        for document in existing_documents:
            try:
                base_id = paper_identity_from_metadata(document).base_id
            except ValueError:
                continue
            current = existing_by_base.get(base_id)
            if current is None or paper_version_sort_key(
                document
            ) > paper_version_sort_key(current):
                existing_by_base[base_id] = document

        paper_operations = []
        archive_operations = []
        for base_id, incoming in canonical_by_base.items():
            current = existing_by_base.get(base_id)
            if current is None:
                paper_operations.append(
                    UpdateOne(
                        {"base_arxiv_id": base_id},
                        {"$set": incoming},
                        upsert=True,
                    )
                )
                continue

            current_canonical = canonicalize_paper_metadata(current)
            current_version = current_canonical.get("arxiv_version")
            incoming_version = incoming.get("arxiv_version")
            current_number = current_version if current_version is not None else -1
            incoming_number = incoming_version if incoming_version is not None else -1

            if incoming_number < current_number:
                archive_operations.append(
                    ReplaceOne(
                        {
                            "base_arxiv_id": base_id,
                            "arxiv_version": incoming_version,
                        },
                        self._archive_document(
                            incoming,
                            reason="older_version_received",
                            replaced_by=current_canonical["arxiv_id"],
                            archived_at=now,
                        ),
                        upsert=True,
                    )
                )
                skipped_older += 1
            elif incoming_number > current_number:
                archive_operations.append(
                    ReplaceOne(
                        {
                            "base_arxiv_id": base_id,
                            "arxiv_version": current_version,
                        },
                        self._archive_document(
                            current_canonical,
                            reason="superseded_by_import",
                            replaced_by=incoming["arxiv_id"],
                            archived_at=now,
                        ),
                        upsert=True,
                    )
                )
                paper_operations.append(
                    ReplaceOne({"_id": current["_id"]}, incoming, upsert=False)
                )
            else:
                paper_operations.append(
                    UpdateOne({"_id": current["_id"]}, {"$set": incoming})
                )

        try:
            if archive_operations:
                self.paper_archive.bulk_write(archive_operations, ordered=True)
                archived = len(archive_operations)
            if paper_operations:
                result = self.papers.bulk_write(paper_operations, ordered=False)
                inserted = result.upserted_count
                updated = result.modified_count
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error: {bwe.details}")
            failed += len(canonical_by_base)
        except PyMongoError as e:
            logger.error(f"MongoDB error during bulk write: {str(e)}")
            failed += len(canonical_by_base)
        except Exception as e:
            logger.exception(f"Unexpected error during bulk write: {str(e)}")
            failed += len(canonical_by_base)

        stats = {
            "event": "paper_ingestion",
            "timestamp": now,
            "inserted": inserted,
            "updated": updated,
            "archived": archived,
            "skipped_older": skipped_older,
            "failed": failed,
            "total_processed": len(papers),
        }

        try:
            self.stats.insert_one(dict(stats))
        except PyMongoError as e:
            logger.warning(f"Could not log ingestion stats: {str(e)}")

        logger.info(
            "Stored %d new papers, updated %d, archived %d, "
            "skipped %d older versions, failed %d",
            inserted,
            updated,
            archived,
            skipped_older,
            failed,
        )
        return stats

    def cleanup_paper_versions(self, *, dry_run: bool = False) -> Dict[str, Any]:
        """Archive superseded versions and normalize the live paper collection."""

        from pymongo import ReplaceOne
        from pymongo.errors import PyMongoError

        before = self.papers.count_documents({})
        plan = build_paper_cleanup_plan(self.papers.find({}))
        result: Dict[str, Any] = {
            "event": "paper_version_cleanup",
            "timestamp": datetime.now(timezone.utc),
            "dry_run": dry_run,
            "documents_before": before,
            "base_papers": plan.base_papers,
            "latest_documents": len(plan.current),
            "archived_documents": plan.archive_count,
            "invalid_documents": len(plan.invalid),
            "documents_after": (
                before if dry_run else len(plan.current) + len(plan.invalid)
            ),
        }
        if dry_run:
            return result

        archived_at = datetime.now(timezone.utc)
        archive_operations = []
        archive_ids = []
        current_by_base = {paper["base_arxiv_id"]: paper for paper in plan.current}
        for paper in plan.archive:
            source_id = paper.get("_id")
            if source_id is not None:
                archive_ids.append(source_id)
            replacement = current_by_base[paper["base_arxiv_id"]]["arxiv_id"]
            archive_operations.append(
                ReplaceOne(
                    {
                        "base_arxiv_id": paper["base_arxiv_id"],
                        "arxiv_version": paper.get("arxiv_version"),
                    },
                    self._archive_document(
                        paper,
                        reason="superseded_version_cleanup",
                        replaced_by=replacement,
                        archived_at=archived_at,
                    ),
                    upsert=True,
                )
            )

        try:
            if archive_operations:
                self.paper_archive.bulk_write(archive_operations, ordered=True)
            if archive_ids:
                self.papers.delete_many({"_id": {"$in": archive_ids}})
            current_operations = [
                ReplaceOne({"_id": paper["_id"]}, paper, upsert=False)
                for paper in plan.current
            ]
            if current_operations:
                self.papers.bulk_write(current_operations, ordered=False)
            self.papers.create_index(
                "base_arxiv_id",
                name="base_arxiv_id_unique",
                unique=True,
                partialFilterExpression={"base_arxiv_id": {"$type": "string"}},
            )
            self.stats.insert_one(dict(result))
        except PyMongoError:
            logger.exception("Paper version cleanup failed")
            raise

        logger.info(
            "Paper cleanup retained %d latest papers and archived %d older versions",
            len(plan.current),
            plan.archive_count,
        )
        return result

    @staticmethod
    def _archive_document(
        paper: Dict[str, Any],
        *,
        reason: str,
        replaced_by: str,
        archived_at: datetime,
    ) -> Dict[str, Any]:
        archived = canonicalize_paper_metadata(paper)
        source_id = archived.pop("_id", None)
        archived.update(
            {
                "source_paper_object_id": str(source_id) if source_id else None,
                "archived_at": archived_at,
                "archive_reason": reason,
                "replaced_by_arxiv_id": replaced_by,
            }
        )
        return archived

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """Retrieve single paper by ID."""
        return self.papers.find_one({"id": paper_id})

    def record_pdf(
        self,
        *,
        paper_id: str,
        arxiv_id: str,
        local_pdf_path: str,
        document_hash: str,
        size_bytes: int,
    ) -> None:
        """Record a portable PDF location on the matching current/archive version."""

        now = datetime.now(timezone.utc)
        identity = paper_identity_from_metadata({"arxiv_id": arxiv_id, "id": paper_id})
        pdf_fields = {
            "local_pdf_path": local_pdf_path,
            "pdf_document_hash": document_hash,
            "pdf_size_bytes": size_bytes,
            "pdf_downloaded_at": now,
        }
        result = self.papers.update_one(
            {"arxiv_id": identity.version_id},
            {"$set": pdf_fields},
        )
        if result.matched_count == 0:
            self.paper_archive.update_one(
                {"arxiv_id": identity.version_id},
                {"$set": pdf_fields},
            )
        self.db["downloaded_pdfs"].update_one(
            {"arxiv_id": identity.version_id},
            {
                "$set": {
                    "arxiv_id": identity.version_id,
                    "downloaded": True,
                    **pdf_fields,
                }
            },
            upsert=True,
        )

    def get_papers(
        self,
        filter_query: Dict = None,
        limit: int = 100,
        skip: int = 0,
        sort_by: str = "published",
        sort_order: int = -1,
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

        cursor = (
            self.papers.find(filter_query)
            .sort(sort_by, sort_order)
            .skip(skip)
            .limit(limit)
        )
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
