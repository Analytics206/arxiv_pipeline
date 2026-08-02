"""Validation and response models for harness feedback batches."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

FEEDBACK_BATCH_CONTRACT = "research-feedback-batch"
FEEDBACK_ACK_CONTRACT: Literal["research-feedback-ack"] = "research-feedback-ack"
FEEDBACK_CONTRACT_VERSION = "1.0"
FEEDBACK_TAXONOMY_VERSION = "1.0"
MAX_FEEDBACK_RECORDS = 100

REASON_GROUPS = {
    "off_topic": "retrieval_defect",
    "superficial_match": "retrieval_defect",
    "not_project_fit": "project_relative",
    "transfer_risk": "project_relative",
    "already_covered": "redundancy",
    "evidence_unresolvable": "evidence_analysis_defect",
    "evidence_mismatch": "evidence_analysis_defect",
    "evidence_truncated": "evidence_analysis_defect",
    "analysis_gap": "evidence_analysis_defect",
    "adopted": "positive",
    "trial": "positive",
    "useful_context": "positive",
    "trial_succeeded": "outcome_follow_up",
    "trial_failed": "outcome_follow_up",
    "adoption_reverted": "outcome_follow_up",
    "coverage_gap": "corpus_demand",
}
KNOWN_REASONS = frozenset(REASON_GROUPS)
PROJECT_ONLY_REASONS = frozenset(
    {
        "not_project_fit",
        "transfer_risk",
        "already_covered",
    }
)

_REASON_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_SUBJECT_KINDS = {"paper", "idea", "evidence", "topic"}
_VERDICTS = {"ADOPT", "TRIAL", "REJECT", "UNVERIFIED"}
_OUTCOME_REASONS = {"trial_succeeded", "trial_failed", "adoption_reverted"}
_KNOWN_REASON_SUBJECTS = {
    "off_topic": {"paper"},
    "superficial_match": {"paper"},
    "not_project_fit": {"paper", "idea"},
    "transfer_risk": {"idea"},
    "already_covered": {"paper"},
    "evidence_unresolvable": {"evidence"},
    "evidence_mismatch": {"evidence"},
    "evidence_truncated": {"evidence"},
    "analysis_gap": {"paper"},
    "adopted": {"idea"},
    "trial": {"idea"},
    "useful_context": {"paper"},
    "trial_succeeded": {"idea"},
    "trial_failed": {"idea"},
    "adoption_reverted": {"idea"},
    "coverage_gap": {"topic"},
}


class FeedbackEnvelopeError(ValueError):
    """The request is not a processable feedback batch envelope."""

    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class FeedbackRecordError(BaseModel):
    index: int = Field(ge=0)
    feedback_id: str | None = None
    error: str


class FeedbackAck(BaseModel):
    contract: Literal["research-feedback-ack"] = FEEDBACK_ACK_CONTRACT
    received: int = Field(ge=0)
    accepted: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    errors: list[FeedbackRecordError] = Field(default_factory=list)
    unknown_reasons: list[str] = Field(default_factory=list)
    unresolved_papers: list[str] = Field(default_factory=list)


def validate_envelope(payload: Any) -> dict[str, Any]:
    """Validate only the batch envelope; records are validated independently."""

    if not isinstance(payload, dict):
        raise FeedbackEnvelopeError("request body must be a JSON object")
    if payload.get("contract") != FEEDBACK_BATCH_CONTRACT:
        raise FeedbackEnvelopeError(f"contract must be '{FEEDBACK_BATCH_CONTRACT}'")
    if payload.get("contract_version") != FEEDBACK_CONTRACT_VERSION:
        raise FeedbackEnvelopeError(
            f"contract_version must be '{FEEDBACK_CONTRACT_VERSION}'"
        )
    try:
        _required_string(payload, "taxonomy_version")
    except ValueError as error:
        raise FeedbackEnvelopeError(str(error)) from error
    _validate_client(payload.get("client"))
    _validate_project(payload.get("project"))

    records = payload.get("records")
    if not isinstance(records, list):
        raise FeedbackEnvelopeError("records must be an array")
    if not records:
        raise FeedbackEnvelopeError("records must contain at least one record")
    if len(records) > MAX_FEEDBACK_RECORDS:
        raise FeedbackEnvelopeError(
            f"records must contain no more than {MAX_FEEDBACK_RECORDS} records",
            status_code=413,
        )
    return payload


def validate_record(record: Any) -> dict[str, Any]:
    """Validate one feedback record while retaining all unknown input fields."""

    if not isinstance(record, dict):
        raise ValueError("record must be a JSON object")

    feedback_id = _required_string(record, "feedback_id")
    if len(feedback_id) > 128:
        raise ValueError("feedback_id must be no longer than 128 characters")

    occurred_at = _required_string(record, "occurred_at")
    _parse_datetime(occurred_at)

    source = _required_string(record, "source")
    if source not in {"agent", "human"}:
        raise ValueError("source must be 'agent' or 'human'")
    if source == "agent":
        _required_string(record, "workflow")
        _required_string(record, "run_id")

    _required_string(record, "stage")
    if "request_id" in record:
        _required_string(record, "request_id")
    reason = _required_string(record, "reason")
    if len(reason) > 40 or _REASON_PATTERN.fullmatch(reason) is None:
        raise ValueError("reason must be snake_case and no longer than 40 characters")

    subject = record.get("subject")
    if not isinstance(subject, dict):
        raise ValueError("subject must be an object")
    kind = _required_string(subject, "kind", prefix="subject.")
    if kind not in _SUBJECT_KINDS:
        raise ValueError("subject.kind must be 'paper', 'idea', 'evidence', or 'topic'")
    if kind in {"paper", "idea", "evidence"}:
        _required_string(subject, "paper_id", prefix="subject.")
    if "point_id" in subject and kind not in {"idea", "evidence"}:
        raise ValueError(
            "subject.point_id is only valid for subject.kind 'idea' or 'evidence'"
        )
    if "point_id" in subject:
        _required_string(subject, "point_id", prefix="subject.")
    if kind == "idea":
        _required_string(subject, "idea_ref", prefix="subject.")
    if kind == "evidence":
        _required_string(subject, "evidence_id", prefix="subject.")
    if kind == "topic":
        _required_string(subject, "topic", prefix="subject.")

    allowed_subjects = _KNOWN_REASON_SUBJECTS.get(reason)
    if allowed_subjects is not None and kind not in allowed_subjects:
        expected = " or ".join(sorted(allowed_subjects))
        raise ValueError(f"reason '{reason}' requires subject.kind {expected!r}")

    verdict = record.get("verdict")
    if verdict is not None and verdict not in _VERDICTS:
        raise ValueError("verdict must be ADOPT, TRIAL, REJECT, or UNVERIFIED")

    note = record.get("note")
    if note is not None:
        if not isinstance(note, str):
            raise ValueError("note must be a string")
        if len(note) > 2000:
            raise ValueError("note must be no longer than 2000 characters")

    if "retrieval" in record:
        _validate_retrieval(record["retrieval"])
    if "queries" in record:
        _validate_queries(record["queries"])
    if reason == "coverage_gap" and not record.get("queries"):
        raise ValueError("reason 'coverage_gap' requires queries")
    if "analysis" in record:
        _validate_analysis(record["analysis"])
    if "corpus" in record:
        _validate_corpus(record["corpus"])

    follow_up_of = record.get("follow_up_of")
    if follow_up_of is not None and (
        not isinstance(follow_up_of, str) or not follow_up_of.strip()
    ):
        raise ValueError("follow_up_of must be a non-empty string")
    if reason in _OUTCOME_REASONS:
        if source != "human":
            raise ValueError(f"reason '{reason}' requires source 'human'")
        if not follow_up_of:
            raise ValueError(f"reason '{reason}' requires follow_up_of")

    return record


def feedback_id_from(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    value = record.get("feedback_id")
    return value if isinstance(value, str) else None


def _required_string(
    value: dict[str, Any],
    field_name: str,
    *,
    prefix: str = "",
) -> str:
    item = value.get(field_name)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{prefix}{field_name} must be a non-empty string")
    return item


def _validate_client(value: Any) -> None:
    if not isinstance(value, dict):
        raise FeedbackEnvelopeError("client must be an object")
    try:
        _required_string(value, "name", prefix="client.")
        _required_string(value, "version", prefix="client.")
    except ValueError as error:
        raise FeedbackEnvelopeError(str(error)) from error


def _validate_project(value: Any) -> None:
    if not isinstance(value, dict):
        raise FeedbackEnvelopeError("project must be an object")
    try:
        _required_string(value, "id", prefix="project.")
    except ValueError as error:
        raise FeedbackEnvelopeError(str(error)) from error


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("occurred_at must be an ISO 8601 datetime") from error


def _validate_retrieval(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("retrieval must be an object")
    _required_string(value, "query", prefix="retrieval.")
    relevance = value.get("relevance")
    if (
        isinstance(relevance, bool)
        or not isinstance(relevance, (int, float))
        or not 0 <= float(relevance) <= 1
    ):
        raise ValueError("retrieval.relevance must be a number from 0 through 1")
    rank = value.get("rank")
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise ValueError("retrieval.rank must be an integer of at least 1")


def _validate_queries(value: Any) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError("queries must be an array of non-empty strings")


def _validate_analysis(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("analysis must be an object")
    for field_name in ("prompt_version", "analysis_model", "profile"):
        if field_name in value:
            _required_string(value, field_name, prefix="analysis.")


def _validate_corpus(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("corpus must be an object")
    for field_name in ("papers", "points"):
        item = value.get(field_name)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError(f"corpus.{field_name} must be a non-negative integer")
