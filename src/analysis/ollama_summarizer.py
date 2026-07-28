"""Hierarchical, evidence-validating paper analysis using structured model output."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Protocol, TypeVar

from pydantic import BaseModel

from src.analysis.cache import JsonChunkAnalysisCache
from src.analysis.identity import PaperIdentity
from src.analysis.models import (
    ChunkAnalysisDraft,
    DraftClaim,
    DraftImplementationIdea,
    EvidenceQuote,
    EvidenceRef,
    ImplementationIdea,
    PaperAnalysis,
    SupportedClaim,
    SynthesisDraft,
)
from src.analysis.evidence_quality import expand_verification_span
from src.analysis.idea_quality import normalize_implementation_idea
from src.analysis.pdf_parser import DocumentChunk, ParsedPaperDocument

TModel = TypeVar("TModel", bound=BaseModel)
logger = logging.getLogger(__name__)


class StructuredModel(Protocol):
    """Provider-neutral interface for schema-constrained generation."""

    model_name: str

    def complete(
        self,
        *,
        schema: type[TModel],
        system: str,
        prompt: str,
    ) -> TModel: ...


class OllamaStructuredModel:
    """Ollama adapter that requests JSON matching a Pydantic schema."""

    def __init__(
        self,
        model_name: str,
        host: str,
        *,
        context_length: int = 12288,
        max_output_tokens: int = 4096,
        retry_context_length: int | None = None,
        retry_max_output_tokens: int | None = None,
        client=None,
    ):
        self.model_name = model_name
        self.context_length = context_length
        self.max_output_tokens = max_output_tokens
        self.retry_context_length = max(
            context_length,
            retry_context_length or context_length,
        )
        self.retry_max_output_tokens = max(
            max_output_tokens,
            retry_max_output_tokens or max_output_tokens,
        )
        if client is None:
            from ollama import Client

            client = Client(host=host, timeout=600)
        self._client = client

    def complete(
        self,
        *,
        schema: type[TModel],
        system: str,
        prompt: str,
    ) -> TModel:
        last_error: Exception | None = None
        previous_was_truncated = False
        for attempt in range(1, 3):
            attempt_prompt = prompt
            if attempt > 1:
                attempt_prompt += _retry_output_instruction(schema)
            context_length = (
                self.retry_context_length
                if previous_was_truncated
                else self.context_length
            )
            max_output_tokens = (
                self.retry_max_output_tokens
                if previous_was_truncated
                else self.max_output_tokens
            )
            response = self._client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": attempt_prompt},
                ],
                format=_ollama_format_schema(schema.model_json_schema()),
                think=False,
                options={
                    "temperature": 0,
                    "num_ctx": context_length,
                    "num_predict": max_output_tokens,
                },
            )
            if isinstance(response, dict):
                content = response["message"]["content"]
            else:
                content = response.message.content
            try:
                if not content or not content.strip():
                    raise ValueError("Ollama returned empty structured content")
                return schema.model_validate_json(content)
            except ValueError as error:
                last_error = error
                done_reason = _response_value(response, "done_reason")
                prompt_tokens = _response_value(response, "prompt_eval_count")
                output_tokens = _response_value(response, "eval_count")
                previous_was_truncated = done_reason == "length" or (
                    _looks_like_truncated_json(content, error)
                )
                logger.warning(
                    "Invalid structured response from %s (attempt %d/2, "
                    "done_reason=%s, prompt_tokens=%s, output_tokens=%s, "
                    "output_chars=%d, num_ctx=%d, num_predict=%d, "
                    "truncated=%s): %s",
                    self.model_name,
                    attempt,
                    done_reason,
                    prompt_tokens,
                    output_tokens,
                    len(content or ""),
                    context_length,
                    max_output_tokens,
                    previous_was_truncated,
                    error,
                )
        raise SummarizationError(
            f"{self.model_name} did not return valid structured content"
        ) from last_error


class SummarizationError(RuntimeError):
    """Raised when a trustworthy analysis cannot be produced."""


def _retry_output_instruction(schema: type[BaseModel]) -> str:
    instruction = (
        "\n\nThe previous response was invalid or truncated. Return a complete "
        "JSON object and close every string, array, and object. Use only the "
        "most important supported items and keep every statement to one concise "
        "sentence."
    )
    if schema is SynthesisDraft:
        instruction += (
            " Hard limits: one TLDR; at most 3 problem items, 6 contributions, "
            "6 methods, 6 results, 4 limitations, 4 implementation ideas, "
            "16 concepts, and 12 tags. Cite at most 3 evidence IDs per item."
        )
    return instruction


def _response_value(response, field_name: str):
    if isinstance(response, dict):
        return response.get(field_name)
    return getattr(response, field_name, None)


def _looks_like_truncated_json(content: str, error: ValueError) -> bool:
    if not content or not content.strip():
        return False
    message = str(error).casefold()
    return (
        "eof while parsing" in message
        or "unexpected eof" in message
        or "end of input" in message
        or not content.rstrip().endswith(("}", "]"))
    )


class EvidenceAwareSummarizer:
    """Map/reduce analyzer that only persists source-verifiable evidence."""

    MAP_SYSTEM = """
You analyze AI research papers for software and coding agents.
Return only the requested structured data. Identify paper-authored claims and
implementation ideas separately. Every claim and idea must include one or more
short, verbatim supporting quotes copied from the supplied pages, with the
correct page number. A quote must directly support the complete statement it is
attached to. Claims are more important than implementation ideas or concepts:
populate every relevant claim category before adding those secondary items.
Do not hide claims in the concepts list. Do not cite the reference list as
evidence of this paper's own results. Do not guess missing details.
""".strip()

    REDUCE_SYSTEM = """
You synthesize verified research notes for coding agents.
Return only the requested structured data. Use only the supplied source items.
Every claim and implementation idea must cite one or more of the supplied
evidence IDs whose supplied quote directly supports the full statement. Do not
invent evidence IDs or broaden a claim beyond its quotes. Clearly preserve
limitations and distinguish reported results from setup details, methods, or
possible engineering applications.
""".strip()

    def __init__(
        self,
        model: StructuredModel,
        *,
        schema_version: str = "1.0",
        prompt_version: str = "agent-paper-v4",
        chunk_max_chars: int = 12_000,
        chunk_cache: JsonChunkAnalysisCache | None = None,
    ):
        self.model = model
        self.schema_version = schema_version
        self.prompt_version = prompt_version
        self.chunk_max_chars = chunk_max_chars
        self.chunk_cache = chunk_cache

    def summarize(
        self,
        *,
        document: ParsedPaperDocument,
        identity: PaperIdentity,
        title: str,
    ) -> PaperAnalysis:
        evidence: dict[str, EvidenceRef] = {}
        mapped: dict[str, list[dict]] = {
            "problem": [],
            "contributions": [],
            "methods": [],
            "results": [],
            "limitations": [],
            "implementation_ideas": [],
        }
        concepts: set[str] = set()

        chunks = document.chunks(self.chunk_max_chars)
        for chunk_index, chunk in enumerate(chunks, start=1):
            logger.info(
                "Analyzing chunk %d/%d (pages %d-%d)",
                chunk_index,
                len(chunks),
                chunk.start_page,
                chunk.end_page,
            )
            draft = self._cached_chunk_draft(document, chunk)
            if draft is None:
                draft = self.model.complete(
                    schema=ChunkAnalysisDraft,
                    system=self.MAP_SYSTEM,
                    prompt=self._map_prompt(title=title, chunk=chunk),
                )
                self._cache_chunk_draft(document, chunk, draft)
            else:
                logger.info(
                    "Using cached analysis for chunk %d/%d",
                    chunk_index,
                    len(chunks),
                )
            for category in (
                "problem",
                "contributions",
                "methods",
                "results",
                "limitations",
            ):
                category_limit = 8 if category == "problem" else 12
                for claim in getattr(draft, category)[:category_limit]:
                    evidence_ids = self._validate_quotes(
                        claim.evidence, chunk, document, evidence
                    )
                    if evidence_ids and _text_supported_by_evidence(
                        claim.statement,
                        evidence_ids,
                        evidence,
                    ):
                        mapped[category].append(
                            {
                                "statement": claim.statement,
                                "evidence_ids": evidence_ids,
                            }
                        )

            for idea in draft.implementation_ideas[:10]:
                evidence_ids = self._validate_quotes(
                    idea.evidence, chunk, document, evidence
                )
                if evidence_ids and _text_supported_by_evidence(
                    idea.agent_use,
                    evidence_ids,
                    evidence,
                    minimum_coverage=0.22,
                ):
                    description = idea.description or idea.agent_use
                    mapped["implementation_ideas"].append(
                        {
                            "title": idea.title or _derived_title(description),
                            "description": description,
                            "agent_use": idea.agent_use,
                            "expected_benefit": idea.expected_benefit,
                            "risks": idea.risks[:8],
                            "evidence_ids": evidence_ids,
                        }
                    )
            concepts.update(
                item.strip() for item in draft.concepts[:30] if item.strip()
            )
            logger.info(
                "Chunk %d/%d complete; %d verified evidence references so far",
                chunk_index,
                len(chunks),
                len(evidence),
            )

        if not evidence:
            raise SummarizationError(
                "The model returned no evidence quotes that could be verified "
                "against the PDF"
            )

        synthesis_input = self._synthesis_input(
            mapped=mapped,
            concepts=concepts,
            evidence=evidence,
        )
        logger.info("Synthesizing %d verified evidence references", len(evidence))
        synthesis = self.model.complete(
            schema=SynthesisDraft,
            system=self.REDUCE_SYSTEM,
            prompt=self._reduce_prompt(title=title, source_items=synthesis_input),
        )
        validated = self._validate_synthesis(
            synthesis,
            evidence=evidence,
            mapped=mapped,
        )
        validated = self._ensure_synthesis_coverage(
            validated,
            mapped=mapped,
            concepts=concepts,
        )
        self._validate_analysis_quality(validated)

        return PaperAnalysis(
            schema_version=self.schema_version,
            prompt_version=self.prompt_version,
            paper_id=identity.base_id,
            paper_version_id=identity.version_id,
            resource_uri=identity.resource_uri,
            title=title,
            document_hash=document.document_hash,
            page_count=document.page_count,
            model=self.model.model_name,
            tldr=validated.tldr,
            problem=validated.problem,
            contributions=validated.contributions,
            methods=validated.methods,
            results=validated.results,
            limitations=validated.limitations,
            implementation_ideas=validated.implementation_ideas,
            concepts=validated.concepts,
            tags=validated.tags,
            evidence=sorted(
                evidence.values(), key=lambda item: (item.page, item.evidence_id)
            ),
        )

    def _validate_quotes(
        self,
        quotes: Iterable[EvidenceQuote],
        chunk: DocumentChunk,
        document: ParsedPaperDocument,
        evidence: dict[str, EvidenceRef],
    ) -> list[str]:
        evidence_ids: list[str] = []
        for proposed in list(quotes)[:5]:
            if not chunk.start_page <= proposed.page <= chunk.end_page:
                continue
            page_text = document.page_text(proposed.page)
            source_quote = _find_source_quote(proposed.quote, page_text)
            if source_quote is None:
                continue
            evidence_id = _evidence_id(
                document.document_hash,
                chunk.chunk_id,
                proposed.page,
                source_quote,
            )
            verification = expand_verification_span(source_quote, page_text)
            if verification.truncated:
                logger.debug(
                    "Rejected incomplete evidence span on page %d: %r",
                    proposed.page,
                    source_quote[:120],
                )
                continue
            evidence[evidence_id] = EvidenceRef(
                evidence_id=evidence_id,
                chunk_id=chunk.chunk_id,
                page=proposed.page,
                quote=verification.quote,
                supporting_quote=verification.supporting_quote,
                truncated=False,
                section=proposed.section,
            )
            evidence_ids.append(evidence_id)
        return list(dict.fromkeys(evidence_ids))

    def _validate_synthesis(
        self,
        synthesis: SynthesisDraft,
        *,
        evidence: dict[str, EvidenceRef],
        mapped: dict[str, list[dict]],
    ) -> SynthesisDraft:
        def clean_claim(claim: SupportedClaim) -> SupportedClaim | None:
            evidence_ids = [item for item in claim.evidence_ids if item in evidence]
            if not evidence_ids or not _text_supported_by_evidence(
                claim.statement,
                evidence_ids,
                evidence,
            ):
                return None
            return claim.model_copy(
                update={"evidence_ids": list(dict.fromkeys(evidence_ids))[:12]}
            )

        def clean_claims(
            claims: list[SupportedClaim], limit: int = 12
        ) -> list[SupportedClaim]:
            return [
                clean
                for claim in claims[:limit]
                if (clean := clean_claim(claim)) is not None
            ]

        def clean_ideas(ideas: list[ImplementationIdea]) -> list[ImplementationIdea]:
            cleaned: list[ImplementationIdea] = []
            for idea in ideas[:12]:
                evidence_ids = [item for item in idea.evidence_ids if item in evidence]
                if evidence_ids and _text_supported_by_evidence(
                    idea.agent_use,
                    evidence_ids,
                    evidence,
                    minimum_coverage=0.22,
                ):
                    cleaned.append(
                        normalize_implementation_idea(
                            idea.model_copy(
                                update={
                                    "evidence_ids": list(dict.fromkeys(evidence_ids))[
                                        :12
                                    ],
                                }
                            )
                        )
                    )
            return cleaned

        tldr = clean_claim(synthesis.tldr)
        if tldr is None:
            tldr = self._fallback_tldr(mapped)
        return synthesis.model_copy(
            update={
                "tldr": tldr,
                "problem": clean_claims(synthesis.problem, limit=8),
                "contributions": clean_claims(synthesis.contributions),
                "methods": clean_claims(synthesis.methods),
                "results": clean_claims(synthesis.results),
                "limitations": clean_claims(synthesis.limitations),
                "implementation_ideas": clean_ideas(synthesis.implementation_ideas),
                "concepts": _clean_concepts(synthesis.concepts)[:40],
                "tags": _unique_clean_strings(synthesis.tags)[:30],
            }
        )

    def _synthesis_input(
        self,
        *,
        mapped: dict[str, list[dict]],
        concepts: set[str],
        evidence: dict[str, EvidenceRef],
    ) -> dict:
        """Attach quote text so the reducer can evaluate its own citations."""

        result: dict[str, object] = {}
        for category in (
            "problem",
            "contributions",
            "methods",
            "results",
            "limitations",
            "implementation_ideas",
        ):
            result[category] = [
                {
                    **item,
                    "evidence_quotes": [
                        {
                            "evidence_id": evidence_id,
                            "page": evidence[evidence_id].page,
                            "quote": evidence[evidence_id].quote,
                        }
                        for evidence_id in item["evidence_ids"]
                        if evidence_id in evidence
                    ],
                }
                for item in mapped[category]
            ]
        result["concepts"] = _clean_concepts(concepts)
        return result

    @staticmethod
    def _fallback_tldr(mapped: dict[str, list[dict]]) -> SupportedClaim:
        """Build a conservative TLDR from an already verified map-stage claim."""

        for category in ("contributions", "results", "methods", "problem"):
            if mapped[category]:
                return SupportedClaim.model_validate(mapped[category][0])
        raise SummarizationError(
            "The synthesized TLDR was unsupported and no verified claim was "
            "available as a fallback"
        )

    @staticmethod
    def _validate_analysis_quality(synthesis: SynthesisDraft) -> None:
        """Refuse to persist a sparse output that is not useful to an agent."""

        populated = sum(
            bool(getattr(synthesis, category))
            for category in (
                "problem",
                "contributions",
                "methods",
                "results",
                "limitations",
            )
        )
        if not synthesis.contributions or populated < 3:
            raise SummarizationError(
                "Analysis quality gate failed: expected contributions and at "
                "least three populated claim categories"
            )

    def _ensure_synthesis_coverage(
        self,
        synthesis: SynthesisDraft,
        *,
        mapped: dict[str, list[dict]],
        concepts: set[str],
    ) -> SynthesisDraft:
        """Keep verified map-stage knowledge if the reducer omits a category."""

        updates: dict[str, object] = {}
        for category in (
            "problem",
            "contributions",
            "methods",
            "results",
            "limitations",
        ):
            if getattr(synthesis, category) or not mapped[category]:
                continue
            limit = 8 if category == "problem" else 12
            updates[category] = [
                SupportedClaim.model_validate(item) for item in mapped[category][:limit]
            ]

        if not synthesis.implementation_ideas and mapped["implementation_ideas"]:
            updates["implementation_ideas"] = [
                ImplementationIdea.model_validate(item)
                for item in mapped["implementation_ideas"][:12]
            ]
        if not synthesis.concepts and concepts:
            updates["concepts"] = sorted(concepts)[:40]
        return synthesis.model_copy(update=updates) if updates else synthesis

    def _map_prompt(self, *, title: str, chunk: DocumentChunk) -> str:
        return (
            f"Paper title: {title}\n"
            f"Pages in this chunk: {chunk.start_page}-{chunk.end_page}\n\n"
            "Extract only information supported by this text. Use these exact "
            "category meanings:\n"
            "- problem: an explicitly stated gap, obstacle, or research need\n"
            "- contributions: what the authors claim this paper introduces\n"
            "- methods: how the proposed system, training, or experiment works\n"
            "- results: measured findings or explicit empirical comparisons; "
            "never setup details\n"
            "- limitations: an explicit failure, caveat, weakness, or boundary\n"
            "- implementation_ideas: a technique a coding-agent system could "
            "reuse; keep this separate from paper-authored claims\n\n"
            "First populate every relevant claim category. Quotes must be "
            "verbatim substrings of the page text and must contain enough "
            "context to support the entire attached statement. Return at most "
            "two claims per category, one implementation idea, and five short "
            "concept names. Keep each evidence quote below sixty words. Concepts "
            "must be plain names only, without quotes, evidence, JSON, or "
            "explanations.\n\n"
            f"{chunk.text}"
        )

    def _cached_chunk_draft(
        self,
        document: ParsedPaperDocument,
        chunk: DocumentChunk,
    ) -> ChunkAnalysisDraft | None:
        if self.chunk_cache is None:
            return None
        return self.chunk_cache.get(
            document_hash=document.document_hash,
            chunk_id=chunk.chunk_id,
            model=self.model.model_name,
            prompt_version=self.prompt_version,
        )

    def _cache_chunk_draft(
        self,
        document: ParsedPaperDocument,
        chunk: DocumentChunk,
        draft: ChunkAnalysisDraft,
    ) -> None:
        if self.chunk_cache is None:
            return
        self.chunk_cache.put(
            draft,
            document_hash=document.document_hash,
            chunk_id=chunk.chunk_id,
            model=self.model.model_name,
            prompt_version=self.prompt_version,
        )

    def _reduce_prompt(self, *, title: str, source_items: dict) -> str:
        return (
            f"Paper title: {title}\n\n"
            "Create a concise engineering-oriented synthesis from these verified "
            "source items. Keep evidence IDs attached to the claims they support."
            "\n\n" + json.dumps(source_items, ensure_ascii=False)
        )


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _find_source_quote(proposed_quote: str, page_text: str) -> str | None:
    """Return exact source text for an exact or near-verbatim model quote."""

    normalized_quote = _normalize_text(proposed_quote)
    if len(normalized_quote) < 8:
        return None
    if proposed_quote.strip() in page_text:
        return proposed_quote.strip()

    token_pattern = re.compile(r"\b\w+\b", re.UNICODE)
    proposed_tokens = [
        match.group(0).casefold() for match in token_pattern.finditer(proposed_quote)
    ]
    page_matches = list(token_pattern.finditer(page_text))
    if len(proposed_tokens) < 6 or len(page_matches) < len(proposed_tokens):
        return None

    page_tokens = [match.group(0).casefold() for match in page_matches]
    window_size = len(proposed_tokens)
    best_ratio = 0.0
    best_start = 0
    for start in range(0, len(page_tokens) - window_size + 1):
        window = page_tokens[start : start + window_size]
        ratio = SequenceMatcher(None, proposed_tokens, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start

    threshold = 0.9 if window_size < 20 else 0.86
    if best_ratio < threshold:
        return None
    start_character = page_matches[best_start].start()
    end_character = page_matches[best_start + window_size - 1].end()
    return page_text[start_character:end_character].strip()


def _evidence_id(document_hash: str, chunk_id: str, page: int, quote: str) -> str:
    payload = f"{document_hash}:{chunk_id}:{page}:{_normalize_text(quote)}".encode(
        "utf-8"
    )
    return f"ev_{hashlib.sha256(payload).hexdigest()[:24]}"


def _unique_clean_strings(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item.strip()))


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "using",
    "we",
    "with",
}


def _content_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\b[\w.-]+\b", value.casefold())
        if len(token) > 2 and token not in _STOP_WORDS
    }


def _text_supported_by_evidence(
    statement: str,
    evidence_ids: Iterable[str],
    evidence: dict[str, EvidenceRef],
    *,
    minimum_coverage: float = 0.3,
) -> bool:
    """Reject citations with too little lexical grounding in their quotes."""

    statement_tokens = _content_tokens(statement)
    if not statement_tokens:
        return False
    quote_tokens: set[str] = set()
    for evidence_id in evidence_ids:
        item = evidence.get(evidence_id)
        if item is not None:
            quote_tokens.update(_content_tokens(item.quote))
    return (
        len(statement_tokens & quote_tokens) / len(statement_tokens) >= minimum_coverage
    )


def _clean_concepts(items: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for raw_item in items:
        item = raw_item.strip()
        lowered = item.casefold()
        if (
            not 2 < len(item) <= 200
            or "evidence_quote" in lowered
            or "page_num" in lowered
            or 'format":' in lowered
            or item.startswith(("{", "["))
        ):
            continue
        cleaned.append(item)
    return list(dict.fromkeys(cleaned))


def _derived_title(description: str) -> str:
    first_sentence = description.strip().split(".", 1)[0].strip()
    if len(first_sentence) < 3:
        return "Derived implementation idea"
    return first_sentence[:200]


def _ollama_format_schema(schema: dict) -> dict:
    """Keep structural JSON Schema while Pydantic enforces value constraints.

    Ollama's grammar sampler supports the structural portion of JSON Schema but
    some releases reject validation-only keywords such as ``maxLength`` and
    ``maxItems``. Removing those keywords affects generation guidance only; the
    original Pydantic model still validates the returned JSON.
    """

    unsupported = {
        "default",
        "description",
        "examples",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "maxLength",
        "maximum",
        "minLength",
        "minimum",
        "multipleOf",
        "pattern",
        "title",
        "uniqueItems",
    }

    def clean(value, *, property_map: bool = False):
        if isinstance(value, dict):
            # Under JSON Schema's ``properties`` keyword, dictionary keys are
            # user-field names. A field legitimately named ``title`` or
            # ``description`` must survive even though schema annotations with
            # those same names are removed elsewhere.
            if property_map:
                return {key: clean(item) for key, item in value.items()}
            return {
                key: clean(item, property_map=key == "properties")
                for key, item in value.items()
                if key not in unsupported
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(schema)
