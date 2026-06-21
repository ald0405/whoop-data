"""Tests for the biomarker knowledge-base ingestion + graceful fallback.

These cover the parts that don't need a live Postgres:
- markdown frontmatter parsing and chunk metadata shape (ingestion),
- the retrieval tool's graceful degradation when the KB is unavailable.

The "no bridging general knowledge to the user's value" contract is a prompt-level
behaviour (docs/features/BIOMARKER_INTENDED_PURPOSE.md, vetted-knowledge amendment)
and is best covered by an eval / manual check, not a unit test.
"""

from __future__ import annotations

import json

import pytest


def test_parse_markdown_splits_frontmatter():
    from whoopdata.knowledge.ingest_biomarker_kb import parse_markdown

    text = (
        "---\n"
        'biomarker: "LDL Cholesterol"\n'
        "slug: ldl-cholesterol\n"
        "source_url: https://withemerald.com/knowledge/biomarker/ldl-cholesterol\n"
        "---\n"
        "# LDL Cholesterol\n\nBody content.\n"
    )
    parsed = parse_markdown(text)

    assert parsed.frontmatter["biomarker"] == "LDL Cholesterol"
    assert parsed.frontmatter["slug"] == "ldl-cholesterol"
    assert parsed.body.startswith("# LDL Cholesterol")
    assert "Body content." in parsed.body


def test_chunk_document_carries_attribution_metadata():
    from whoopdata.knowledge.ingest_biomarker_kb import ParsedDoc, chunk_document

    parsed = ParsedDoc(
        frontmatter={
            "biomarker": "LDL Cholesterol",
            "source": "Emerald",
            "source_url": "https://withemerald.com/knowledge/biomarker/ldl-cholesterol",
        },
        body="# LDL Cholesterol\n\n## What it is\n\nLDL carries cholesterol.\n",
    )
    docs = chunk_document(parsed, slug="ldl-cholesterol")

    assert docs, "expected at least one chunk"
    for doc in docs:
        assert doc.metadata["biomarker"] == "LDL Cholesterol"
        assert doc.metadata["source"] == "Emerald"
        assert doc.metadata["source_url"].endswith("ldl-cholesterol")
        assert doc.metadata["section"]  # heading captured


@pytest.mark.anyio
async def test_knowledge_tool_graceful_when_kb_unavailable(monkeypatch):
    """When the KB store can't be built, the tool returns a fallback note."""
    import whoopdata.knowledge.biomarker_kb as kb
    from whoopdata.agent.tools import get_biomarker_knowledge_tool

    monkeypatch.setattr(kb, "get_kb_store", lambda *a, **k: None)

    raw = await get_biomarker_knowledge_tool.coroutine(
        query="what is LDL", biomarker="LDL Cholesterol"
    )
    payload = json.loads(raw)

    assert payload["passages"] == []
    assert "unavailable" in payload["note"].lower()
