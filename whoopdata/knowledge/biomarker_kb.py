"""Shared pgvector store for the biomarker knowledge base (Emerald RAG).

This is the single construction point used by both the ingestion script
(``ingest_biomarker_kb``) and the runtime retrieval tool
(``get_biomarker_knowledge`` in ``whoopdata.agent.tools``).

Design notes / boundary:
- The KB is a **general, non-personalised, source-attributed library** of vetted
  Emerald content. It is not applied to an individual's data. See
  ``docs/features/BIOMARKER_INTENDED_PURPOSE.md``.
- Construction is best-effort: if Postgres is unavailable or the dependency is
  missing, ``get_kb_store`` returns ``None`` so callers can degrade gracefully
  (the agent falls back to the DB-backed ``get_biomarker_education`` glossary).
"""

from __future__ import annotations

from typing import Any, Optional

from whoopdata.agent import settings


def _normalise_url(url: str) -> str:
    """Coerce a libpq URL to the psycopg3 SQLAlchemy driver form.

    ``AGENT_POSTGRES_URL`` is typically ``postgresql://...?sslmode=disable``;
    langchain-postgres builds a SQLAlchemy engine and needs the explicit
    ``postgresql+psycopg://`` driver. ``sslmode`` is left intact (psycopg3
    accepts it as a connection keyword).
    """
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def get_embeddings() -> Any:
    """Return the OpenAI embeddings client used for the KB."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=settings.BIOMARKER_KB_EMBEDDING_MODEL)


def get_kb_store(create_extension: bool = False) -> Optional[Any]:
    """Return the PGVector store for the biomarker KB, or ``None`` if unavailable.

    Args:
        create_extension: When True (ingestion path), ensure the pgvector
            extension and collection tables exist. The runtime tool leaves this
            False to avoid DDL on the hot path.
    """
    url = settings.BIOMARKER_KB_POSTGRES_URL
    if not url:
        return None
    try:
        from langchain_postgres import PGVector

        return PGVector(
            embeddings=get_embeddings(),
            collection_name=settings.BIOMARKER_KB_COLLECTION,
            connection=_normalise_url(url),
            use_jsonb=True,
            create_extension=create_extension,
        )
    except Exception:
        # Missing dependency, Postgres down, or pgvector not installed server-side.
        return None
