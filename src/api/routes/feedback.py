"""Trusted-LAN write endpoint for append-only external harness feedback."""

from __future__ import annotations

import json
import logging
import os
import secrets
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from src.feedback.models import (
    FeedbackAck,
    FeedbackEnvelopeError,
    FeedbackRecordError,
    KNOWN_REASONS,
    feedback_id_from,
    validate_envelope,
    validate_record,
)
from src.feedback.repository import MongoFeedbackRepository
from src.retrieval.factory import load_project_config

router = APIRouter()
logger = logging.getLogger(__name__)


def authorize_feedback(request: Request) -> None:
    expected = os.getenv("RESEARCH_FEEDBACK_BEARER_TOKEN", "").strip()
    if not expected:
        return
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not secrets.compare_digest(supplied, expected)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing feedback bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_feedback_repository() -> Iterator[MongoFeedbackRepository]:
    config = load_project_config()
    mongo = config.get("mongo", {})
    feedback = config.get("research_feedback", {})
    analysis = config.get("analysis", {})
    discovery = config.get("discovery_index", {})
    repository = MongoFeedbackRepository(
        connection_string=os.getenv(
            "MONGO_CONNECTION_STRING",
            mongo.get("connection_string_local", "mongodb://localhost:27017/"),
        ),
        db_name=os.getenv("MONGO_DB", mongo.get("db_name", "arxiv_papers")),
        collection_name=os.getenv(
            "MONGO_FEEDBACK_COLLECTION",
            str(feedback.get("collection_name") or "harness_feedback"),
        ),
        papers_collection=str(feedback.get("papers_collection") or "papers"),
        kaggle_collection=str(
            feedback.get("kaggle_collection")
            or discovery.get("source_collection")
            or "arxiv_kaggle"
        ),
        analyses_collection=str(
            feedback.get("analyses_collection")
            or analysis.get("collection_name")
            or "paper_analyses"
        ),
    )
    try:
        yield repository
    finally:
        repository.close()


FeedbackRepository = Annotated[
    MongoFeedbackRepository,
    Depends(get_feedback_repository),
]
AuthorizedFeedback = Annotated[None, Depends(authorize_feedback)]


@router.post(
    "/feedback",
    response_model=FeedbackAck,
    operation_id="submit_research_feedback",
    summary="Append a batch of external harness judgments",
    responses={
        400: {"description": "Malformed batch envelope"},
        401: {"description": "Feedback bearer token rejected"},
        413: {"description": "More than 100 feedback records"},
        503: {"description": "Feedback store unavailable"},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": [
                            "contract",
                            "contract_version",
                            "taxonomy_version",
                            "client",
                            "project",
                            "records",
                        ],
                        "properties": {
                            "contract": {
                                "type": "string",
                                "const": "research-feedback-batch",
                            },
                            "contract_version": {
                                "type": "string",
                                "const": "1.0",
                            },
                            "taxonomy_version": {"type": "string"},
                            "client": {"type": "object"},
                            "project": {"type": "object"},
                            "records": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 100,
                                "items": {"type": "object"},
                            },
                        },
                    }
                }
            },
        }
    },
)
async def submit_research_feedback(
    request: Request,
    _authorization: AuthorizedFeedback,
    repository: FeedbackRepository,
) -> FeedbackAck:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="Malformed JSON body") from error

    try:
        envelope = validate_envelope(payload)
    except FeedbackEnvelopeError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=str(error),
        ) from error

    errors: list[FeedbackRecordError] = []
    valid_records: list[dict[str, Any]] = []
    for index, record in enumerate(envelope["records"]):
        try:
            valid_records.append(validate_record(record))
        except ValueError as error:
            errors.append(
                FeedbackRecordError(
                    index=index,
                    feedback_id=feedback_id_from(record),
                    error=str(error),
                )
            )

    accepted = 0
    duplicates = 0
    unresolved_papers: list[str] = []
    try:
        for record in valid_records:
            inserted, paper_resolved = repository.append(
                envelope=envelope,
                record=record,
            )
            if inserted:
                accepted += 1
            else:
                duplicates += 1
            paper_id = record["subject"].get("paper_id")
            if paper_id and not paper_resolved:
                unresolved_papers.append(str(paper_id))
    except Exception as error:
        logger.exception("Feedback store is unavailable")
        raise HTTPException(
            status_code=503,
            detail="Feedback store unavailable",
        ) from error

    unknown_reasons = [
        reason
        for reason in dict.fromkeys(str(record["reason"]) for record in valid_records)
        if reason not in KNOWN_REASONS
    ]
    return FeedbackAck(
        received=len(envelope["records"]),
        accepted=accepted,
        duplicates=duplicates,
        errors=errors,
        unknown_reasons=unknown_reasons,
        unresolved_papers=list(dict.fromkeys(unresolved_papers)),
    )
