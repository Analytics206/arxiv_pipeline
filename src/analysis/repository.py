"""MongoDB persistence for versioned paper analyses."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient

from src.analysis.identity import normalize_arxiv_id, paper_lookup_aliases
from src.analysis.models import (
    AgentPaperContext,
    EvidenceResource,
    PaperAnalysis,
    PaperCatalogItem,
    PaperCatalogResponse,
)


class AnalysisRepository:
    """Treat MongoDB analyses as canonical and other indexes as rebuildable."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers",
        collection_name: str = "paper_analyses",
        *,
        database: Any | None = None,
    ):
        self._client = None
        if database is None:
            self._client = MongoClient(connection_string)
            database = self._client[db_name]
        self.db = database
        self.papers = database["papers"]
        self.analyses = database[collection_name]
        self._setup_indexes()

    def _setup_indexes(self) -> None:
        self.analyses.create_index(
            [
                ("paper_id", 1),
                ("document_hash", 1),
                ("schema_version", 1),
                ("prompt_version", 1),
                ("model", 1),
            ],
            unique=True,
            name="analysis_identity",
        )
        self.analyses.create_index(
            [("paper_id", 1), ("generated_at", -1)],
            name="latest_analysis",
        )
        self.analyses.create_index(
            [("evidence.evidence_id", 1)],
            name="evidence_lookup",
        )

    def find_paper(self, paper_id: str) -> dict[str, Any] | None:
        """Resolve raw IDs and common arXiv URL variants."""

        try:
            identity = normalize_arxiv_id(paper_id)
            aliases = paper_lookup_aliases(paper_id)
            query = {
                "$or": [
                    {"id": {"$in": aliases}},
                    {"arxiv_id": {"$in": [identity.version_id, identity.base_id]}},
                    {"base_arxiv_id": identity.base_id},
                    {"pdf_url": {"$in": aliases}},
                ]
            }
        except ValueError:
            query = {"id": paper_id}
        paper = self.papers.find_one(query)
        return _public_document(paper) if paper else None

    def find_exact_analysis(self, analysis: PaperAnalysis) -> PaperAnalysis | None:
        return self.find_matching_analysis(
            paper_id=analysis.paper_id,
            document_hash=analysis.document_hash,
            schema_version=analysis.schema_version,
            prompt_version=analysis.prompt_version,
            model=analysis.model,
        )

    def find_matching_analysis(
        self,
        *,
        paper_id: str,
        document_hash: str,
        schema_version: str,
        prompt_version: str,
        model: str,
    ) -> PaperAnalysis | None:
        identity = normalize_arxiv_id(paper_id)
        query = {
            "paper_id": identity.base_id,
            "document_hash": document_hash,
            "schema_version": schema_version,
            "prompt_version": prompt_version,
            "model": model,
        }
        return _analysis_from_document(self.analyses.find_one(query))

    def save_analysis(self, analysis: PaperAnalysis) -> str:
        """Upsert one immutable analysis version and mark it current."""

        analysis_id = _analysis_id(analysis)
        now = datetime.now(timezone.utc)
        document = analysis.model_dump(mode="python")
        document.update(
            {
                "_id": analysis_id,
                "analysis_id": analysis_id,
                "is_current": True,
                "updated_at": now,
            }
        )
        self.analyses.update_many(
            {"paper_id": analysis.paper_id, "_id": {"$ne": analysis_id}},
            {"$set": {"is_current": False}},
        )
        self.analyses.replace_one({"_id": analysis_id}, document, upsert=True)
        return analysis_id

    def get_latest_analysis(self, paper_id: str) -> PaperAnalysis | None:
        identity = normalize_arxiv_id(paper_id)
        document = self.analyses.find_one(
            {"paper_id": identity.base_id},
            sort=[("is_current", -1), ("generated_at", -1)],
        )
        return _analysis_from_document(document)

    def get_agent_context(self, paper_id: str) -> AgentPaperContext | None:
        paper = self.find_paper(paper_id)
        analysis = self.get_latest_analysis(paper_id)
        if analysis is None:
            return None
        return AgentPaperContext(
            resource_uri=analysis.resource_uri,
            paper=paper
            or {
                "id": analysis.paper_version_id,
                "title": analysis.title,
            },
            analysis=analysis,
        )

    def list_current_analyses(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> PaperCatalogResponse:
        query = {"is_current": True}
        total = self.analyses.count_documents(query)
        cursor = (
            self.analyses.find(query)
            .sort("generated_at", -1)
            .skip(offset)
            .limit(limit)
        )
        papers = [
            _catalog_item_from_analysis(analysis)
            for document in cursor
            if (analysis := _analysis_from_document(document)) is not None
        ]
        return PaperCatalogResponse(
            total=total,
            offset=offset,
            limit=limit,
            papers=papers,
        )

    def get_current_analyses(
        self,
        *,
        paper_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[PaperAnalysis]:
        """Return canonical analyses for rebuildable indexing/evaluation work."""

        query: dict[str, Any] = {"is_current": True}
        if paper_ids:
            query["paper_id"] = {
                "$in": [
                    normalize_arxiv_id(paper_id).base_id
                    for paper_id in dict.fromkeys(paper_ids)
                ]
            }
        cursor = self.analyses.find(query).sort("generated_at", -1).limit(limit)
        return [
            analysis
            for document in cursor
            if (analysis := _analysis_from_document(document)) is not None
        ]

    def get_evidence(self, evidence_id: str) -> EvidenceResource | None:
        document = self.analyses.find_one(
            {
                "is_current": True,
                "evidence.evidence_id": evidence_id,
            },
            sort=[("generated_at", -1)],
        )
        analysis = _analysis_from_document(document)
        if analysis is None:
            return None
        evidence = next(
            (
                item
                for item in analysis.evidence
                if item.evidence_id == evidence_id
            ),
            None,
        )
        if evidence is None:
            return None
        return EvidenceResource(
            evidence_uri=f"{analysis.resource_uri}#evidence/{evidence_id}",
            paper_resource_uri=analysis.resource_uri,
            paper_id=analysis.paper_id,
            paper_version_id=analysis.paper_version_id,
            title=analysis.title,
            document_hash=analysis.document_hash,
            prompt_version=analysis.prompt_version,
            analysis_model=analysis.model,
            evidence=evidence,
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def __enter__(self) -> "AnalysisRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def _analysis_id(analysis: PaperAnalysis) -> str:
    raw = ":".join(
        [
            analysis.paper_id,
            analysis.document_hash,
            analysis.schema_version,
            analysis.prompt_version,
            analysis.model,
        ]
    ).encode("utf-8")
    return f"analysis_{hashlib.sha256(raw).hexdigest()}"


def _catalog_item_from_analysis(analysis: PaperAnalysis) -> PaperCatalogItem:
    claim_count = 1 + sum(
        len(getattr(analysis, field_name))
        for field_name in (
            "problem",
            "contributions",
            "methods",
            "results",
            "limitations",
        )
    )
    return PaperCatalogItem(
        paper_id=analysis.paper_id,
        paper_version_id=analysis.paper_version_id,
        resource_uri=analysis.resource_uri,
        title=analysis.title,
        generated_at=analysis.generated_at,
        model=analysis.model,
        page_count=analysis.page_count,
        concepts=analysis.concepts,
        tags=analysis.tags,
        evidence_count=len(analysis.evidence),
        claim_count=claim_count,
        implementation_idea_count=len(analysis.implementation_ideas),
    )


def _analysis_from_document(document: dict | None) -> PaperAnalysis | None:
    if document is None:
        return None
    fields = PaperAnalysis.model_fields
    return PaperAnalysis.model_validate(
        {key: value for key, value in document.items() if key in fields}
    )


def _public_document(document: dict | None) -> dict[str, Any] | None:
    if document is None:
        return None
    return {key: _json_safe(value) for key, value in document.items() if key != "_id"}


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value
