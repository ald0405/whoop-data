"""Ingest vetted Emerald biomarker markdown into the pgvector knowledge base.

Run with::

    python -m whoopdata.knowledge.ingest_biomarker_kb [--dir data/knowledge/biomarkers]

Input contract — one markdown file per biomarker with YAML frontmatter::

    ---
    biomarker: "LDL Cholesterol"
    slug: ldl-cholesterol
    source: Emerald
    source_url: https://withemerald.com/knowledge/biomarker/ldl-cholesterol
    retrieved_at: 2026-06-20
    ---
    # LDL Cholesterol
    ...vetted body content...

Idempotent: each chunk is written with a deterministic id (``<slug>-<n>``), so
re-running upserts rather than duplicating.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from whoopdata.knowledge.biomarker_kb import get_kb_store

DEFAULT_DIR = Path("data/knowledge/biomarkers")

_HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]


@dataclass
class ParsedDoc:
    frontmatter: dict
    body: str


def parse_markdown(text: str) -> ParsedDoc:
    """Split YAML frontmatter from the markdown body.

    Tolerant of frontmatter that isn't strictly valid YAML — some scraped values
    contain unquoted colons (e.g. ``normal_range: Male: 40-54% Female: 37-47%``),
    which breaks ``yaml.safe_load``. On any parse error we fall back to a simple
    split-on-first-colon parse so the file is still ingested.
    """
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            raw_fm = parts[1]
            try:
                fm = yaml.safe_load(raw_fm) or {}
                if not isinstance(fm, dict):
                    raise ValueError("frontmatter is not a mapping")
            except Exception:
                fm = _parse_frontmatter_lenient(raw_fm)
            return ParsedDoc(frontmatter=fm, body=parts[2].strip())
    return ParsedDoc(frontmatter={}, body=text.strip())


def _parse_frontmatter_lenient(raw: str) -> dict:
    """Parse ``key: value`` lines, tolerating colons inside the value."""
    out: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def chunk_document(parsed: ParsedDoc, slug: str, category: str = None) -> list[Document]:
    """Chunk a parsed biomarker doc, preserving section headings in metadata.

    Tolerant of two frontmatter dialects: the Emerald scrape (``title`` / ``source`` /
    ``health_area``) and the earlier hand-authored form (``biomarker`` / ``source_url``).
    """
    fm = parsed.frontmatter
    biomarker = fm.get("title") or fm.get("biomarker") or slug
    base_meta = {
        "biomarker": biomarker,
        "slug": slug,
        "category": fm.get("health_area") or fm.get("category") or category,
        "type": fm.get("type"),
        "normal_range": fm.get("normal_range"),
        "source": "Emerald",
        # Emerald scrape stores the page URL in `source`; older form used `source_url`.
        "source_url": fm.get("source_url") or fm.get("source"),
    }
    base_meta = {k: v for k, v in base_meta.items() if v is not None}

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADERS_TO_SPLIT_ON, strip_headers=False
    )
    sections = header_splitter.split_text(parsed.body)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    docs: list[Document] = []
    for section in sections:
        section_name = (
            section.metadata.get("h3")
            or section.metadata.get("h2")
            or section.metadata.get("h1")
            or biomarker
        )
        for piece in text_splitter.split_text(section.page_content):
            meta = dict(base_meta)
            meta["section"] = section_name
            docs.append(Document(page_content=piece, metadata=meta))
    return docs


def ingest(directory: Path) -> int:
    """Embed and upsert every markdown file in ``directory``. Returns chunk count."""
    _skip = {"readme.md", "index.md"}
    files = [p for p in sorted(directory.rglob("*.md")) if p.name.lower() not in _skip]
    if not files:
        print(f"No markdown files found in {directory}", file=sys.stderr)
        return 0

    store = get_kb_store(create_extension=True)
    if store is None:
        print(
            "Knowledge base unavailable (Postgres/pgvector not reachable). "
            "Is the postgres container up and BIOMARKER_KB_POSTGRES_URL set?",
            file=sys.stderr,
        )
        sys.exit(1)

    total = 0
    for path in files:
        parsed = parse_markdown(path.read_text(encoding="utf-8"))
        slug = parsed.frontmatter.get("slug") or path.stem
        # Category folder (e.g. "heart-health") when the corpus is nested.
        category = path.parent.name if path.parent != directory else None
        docs = chunk_document(parsed, slug, category=category)
        if not docs:
            print(f"  {path.name}: no content, skipped")
            continue
        # Stable id keyed by relative path so re-runs upsert and slugs can't collide
        # across categories.
        key = path.relative_to(directory).with_suffix("").as_posix()
        ids = [f"{key}-{i}" for i in range(len(docs))]
        store.add_documents(docs, ids=ids)
        total += len(docs)
        print(f"  {path.relative_to(directory)}: {len(docs)} chunks")

    print(f"Ingested {total} chunks from {len(files)} files.")
    return total


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args(argv)
    ingest(args.dir)


if __name__ == "__main__":
    main()
