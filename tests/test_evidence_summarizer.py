import json

import pytest

from src.analysis.identity import normalize_arxiv_id
from src.analysis.models import (
    ChunkAnalysisDraft,
    SynthesisDraft,
)
from src.analysis.ollama_summarizer import (
    EvidenceAwareSummarizer,
    OllamaStructuredModel,
    SummarizationError,
    _find_source_quote,
    _ollama_format_schema,
)
from src.analysis.pdf_parser import PageText, ParsedPaperDocument


class FakeStructuredModel:
    model_name = "fake-model"

    def __init__(self, quote: str):
        self.quote = quote

    def complete(self, *, schema, system, prompt):
        if schema is ChunkAnalysisDraft:
            supported_claim = {
                "statement": "Long agent trajectories lose useful task context.",
                "evidence": [{"page": 1, "quote": self.quote}],
            }
            return schema.model_validate(
                {
                    "problem": [supported_claim],
                    "contributions": [supported_claim],
                    "methods": [supported_claim],
                    "results": [],
                    "limitations": [],
                    "implementation_ideas": [
                        {
                            "title": "Checkpointed agent memory",
                            "description": (
                                "Persist compact checkpoints during long tasks."
                            ),
                            "agent_use": (
                                "Prevent long agent trajectories from losing "
                                "useful task context."
                            ),
                            "expected_benefit": "Reduce context loss.",
                            "risks": ["A bad checkpoint can preserve an error."],
                            "evidence": [{"page": 1, "quote": self.quote}],
                        }
                    ],
                    "concepts": ["agent memory"],
                }
            )

        assert schema is SynthesisDraft
        source_items = json.loads(prompt[prompt.index("{") :])
        evidence_id = source_items["problem"][0]["evidence_ids"][0]

        def synthesis_items(category):
            return [
                {key: value for key, value in item.items() if key != "evidence_quotes"}
                for item in source_items[category]
            ]

        return schema.model_validate(
            {
                "tldr": {
                    "statement": (
                        "The paper addresses context loss in long agent tasks."
                    ),
                    "evidence_ids": [evidence_id, "invented-evidence"],
                },
                "problem": synthesis_items("problem"),
                "contributions": synthesis_items("contributions"),
                "methods": synthesis_items("methods"),
                "results": [],
                "limitations": [],
                "implementation_ideas": synthesis_items("implementation_ideas"),
                "concepts": ["agent memory"],
                "tags": ["coding agents"],
            }
        )


def make_document() -> ParsedPaperDocument:
    return ParsedPaperDocument(
        path=None,
        document_hash="a" * 64,
        pages=(
            PageText(
                number=1,
                text=(
                    "Long agent trajectories lose useful task context. "
                    "We introduce durable checkpoints for agent memory."
                ),
            ),
        ),
    )


def test_summarizer_keeps_only_verified_evidence_ids():
    quote = "Long agent trajectories lose useful task context."
    summarizer = EvidenceAwareSummarizer(FakeStructuredModel(quote))

    analysis = summarizer.summarize(
        document=make_document(),
        identity=normalize_arxiv_id("2504.18538v1"),
        title="Durable Context for Coding Agents",
    )

    assert analysis.paper_id == "2504.18538"
    assert analysis.evidence[0].quote == quote
    assert analysis.tldr.evidence_ids == [analysis.evidence[0].evidence_id]
    assert analysis.implementation_ideas[0].evidence_ids == [
        analysis.evidence[0].evidence_id
    ]


def test_summarizer_rejects_unverifiable_quotes():
    summarizer = EvidenceAwareSummarizer(
        FakeStructuredModel("This sentence is not in the paper at all.")
    )

    with pytest.raises(SummarizationError, match="no evidence quotes"):
        summarizer.summarize(
            document=make_document(),
            identity=normalize_arxiv_id("2504.18538v1"),
            title="Durable Context for Coding Agents",
        )


def test_ollama_wire_schema_omits_unsupported_validation_keywords():
    wire_schema = _ollama_format_schema(
        {
            "title": "Example",
            "type": "object",
            "properties": {
                "title": {
                    "title": "Generated title",
                    "description": "A required output field.",
                    "type": "string",
                    "minLength": 3,
                },
                "description": {
                    "title": "Generated description",
                    "type": "string",
                    "minLength": 8,
                },
                "name": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 20,
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
            "required": ["name"],
        }
    )

    assert wire_schema == {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "name": {"type": "string"},
            "items": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        },
        "required": ["name"],
    }


def test_near_verbatim_quote_is_mapped_back_to_exact_source():
    source = (
        "The harness records model calls as training data for a standard "
        "reinforcement-learning codebase."
    )
    proposed = (
        "The harness records model calls as training data for a standard "
        "reinforcement learning codebase."
    )

    assert _find_source_quote(proposed, source) == source.rstrip(".")


def test_empty_draft_quote_is_not_accepted_as_evidence():
    assert _find_source_quote("", "Any source page text") is None


class FakeOllamaClient:
    def __init__(self):
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return {
                "message": {
                    "content": (
                        '{"tldr":{"statement":"A complete statement",'
                        '"evidence_ids":["ev_123'
                    )
                },
                "done_reason": "length",
                "prompt_eval_count": 9000,
                "eval_count": 4096,
            }
        return {
            "message": {
                "content": json.dumps(
                    {
                        "tldr": {
                            "statement": "A complete supported statement.",
                            "evidence_ids": ["ev_123"],
                        },
                        "problem": [],
                        "contributions": [],
                        "methods": [],
                        "results": [],
                        "limitations": [],
                        "implementation_ideas": [],
                        "concepts": [],
                        "tags": [],
                    }
                )
            },
            "done_reason": "stop",
            "prompt_eval_count": 9100,
            "eval_count": 200,
        }


def test_truncated_ollama_json_retries_with_larger_generation_budget():
    client = FakeOllamaClient()
    model = OllamaStructuredModel(
        "qwen3.5:4b",
        "http://ollama.invalid",
        context_length=12288,
        max_output_tokens=4096,
        retry_context_length=18432,
        retry_max_output_tokens=6144,
        client=client,
    )

    result = model.complete(
        schema=SynthesisDraft,
        system="Return JSON.",
        prompt="Synthesize verified evidence.",
    )

    assert result.tldr.statement == "A complete supported statement."
    assert client.calls[0]["options"]["num_ctx"] == 12288
    assert client.calls[0]["options"]["num_predict"] == 4096
    assert client.calls[1]["options"]["num_ctx"] == 18432
    assert client.calls[1]["options"]["num_predict"] == 6144
    assert "at most 3 problem items" in client.calls[1]["messages"][1]["content"]
