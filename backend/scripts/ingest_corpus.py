#!/usr/bin/env python3
"""
Corpus ingestion CLI for Sancta Nexus Church Knowledge Base.

Loads seed JSON files and optionally fetches documents from Vatican.va,
embeds them, and upserts into the appropriate Qdrant collections.

Usage:
    # Ingest all seed data (local JSON files)
    python -m scripts.ingest_corpus --seed-only

    # Ingest a specific collection from seed data
    python -m scripts.ingest_corpus --seed-only --collection katechizm

    # Ingest everything (seed + remote fetch)
    python -m scripts.ingest_corpus --all

    # Check collection stats
    python -m scripts.ingest_corpus --stats

    # Clear and re-ingest a collection
    python -m scripts.ingest_corpus --seed-only --collection biblia_pl --reset
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

# Adjust sys.path so the script works both via `python scripts/ingest_corpus.py`
# and via `python -m scripts.ingest_corpus` from the backend/ directory.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest_corpus")

# ---------------------------------------------------------------------------
# Seed file registry
# ---------------------------------------------------------------------------

SEED_DIR = _BACKEND_ROOT / "data" / "corpus"

SEED_FILES: dict[str, list[str]] = {
    "katechizm": ["seed_catechism.json"],
    "biblia_pl": ["seed_bible.json"],
    "biblia_la": ["seed_bible.json"],
    "biblia_en": ["seed_bible.json"],
    "sobory": ["seed_councils.json"],
    "magisterium": ["seed_encyclicals.json"],
    "patrystyka": ["seed_patristic.json"],
    "liturgia": [],  # no seed yet
}

# Which translations belong to which collection
TRANSLATION_TO_COLLECTION: dict[str, str] = {
    "BG": "biblia_pl",
    "BT5": "biblia_pl",
    "VUL": "biblia_la",
    "DRB": "biblia_en",
    "GNT": "biblia_en",
    "BHQ": "biblia_la",
}


def _chunk_id(doc_id: str, section_ref: str) -> str:
    """Generate a deterministic UUID from doc_id + section_ref."""
    seed = f"{doc_id}::{section_ref}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _load_seed_file(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _route_chunk(chunk: dict) -> str:
    """Determine target Qdrant collection for a seed chunk."""
    source_type = chunk.get("source_type", "")
    if source_type == "bible":
        translation = chunk.get("translation", "")
        return TRANSLATION_TO_COLLECTION.get(translation, "biblia_pl")
    if source_type == "catechism":
        return "katechizm"
    if source_type == "council":
        return "sobory"
    if source_type == "magisterium":
        return "magisterium"
    if source_type == "patristic":
        return "patrystyka"
    if source_type == "liturgical":
        return "liturgia"
    return "magisterium"


def _build_payload(chunk: dict, collection: str) -> dict:
    """Normalise a seed chunk into a Qdrant payload."""
    payload: dict = {
        "content": chunk["content"],
        "doc_id": chunk.get("doc_id", ""),
        "doc_type": chunk.get("doc_type", ""),
        "source_type": chunk.get("source_type", ""),
        "language": chunk.get("language", "pl"),
        "theology_tags": chunk.get("theology_tags", []),
        "tradition_tags": chunk.get("tradition_tags", ["all"]),
        "section_ref": chunk.get("section_ref", ""),
        "document_title": chunk.get("document_title", ""),
        "year": chunk.get("year"),
        "author": chunk.get("author", ""),
        "collection": collection,
    }

    # Collection-specific extra fields
    source_type = chunk.get("source_type", "")
    if source_type == "bible":
        payload.update({
            "book": chunk.get("book", ""),
            "book_full": chunk.get("book_full", ""),
            "chapter": chunk.get("chapter", 0),
            "verse": chunk.get("verse", 0),
            "verse_end": chunk.get("verse_end"),
            "translation": chunk.get("translation", ""),
        })
    elif source_type == "catechism":
        payload.update({
            "paragraph_ref": chunk.get("section_ref", ""),
            "part": chunk.get("part"),
        })
    elif source_type == "council":
        payload.update({
            "article": chunk.get("article"),
            "document_title_pl": chunk.get("document_title_pl", ""),
        })
    elif source_type == "magisterium":
        payload.update({
            "paragraph": chunk.get("paragraph"),
            "document_title_pl": chunk.get("document_title_pl", ""),
        })
    elif source_type == "patristic":
        payload.update({
            "document_title_pl": chunk.get("document_title_pl", ""),
        })

    return payload


async def ensure_collections(manager) -> None:
    """Create all Qdrant collections if they don't exist."""
    logger.info("Ensuring all Qdrant collections exist...")
    await manager.ensure_all_collections()
    logger.info("Collections ready.")


async def ingest_seed_chunks(
    chunks: list[dict],
    embedding_service,
    manager,
    *,
    collection_filter: str | None = None,
    batch_size: int = 16,
) -> dict[str, int]:
    """Embed and upsert a list of seed chunks into Qdrant.

    Returns a dict of {collection: count} for reporting.
    """
    from qdrant_client.models import PointStruct

    counts: dict[str, int] = {}
    batch: list[tuple[str, PointStruct]] = []

    async def _flush(batch: list[tuple[str, PointStruct]]) -> None:
        if not batch:
            return
        # Group by collection
        by_col: dict[str, list[PointStruct]] = {}
        for col, pt in batch:
            by_col.setdefault(col, []).append(pt)
        for col, points in by_col.items():
            await manager.async_upsert_chunks(col, points)
            counts[col] = counts.get(col, 0) + len(points)
            logger.debug("Upserted %d points to %s", len(points), col)

    texts_to_embed: list[str] = []
    meta_list: list[tuple[str, str, dict]] = []  # (chunk_id, collection, payload)

    for chunk in chunks:
        collection = _route_chunk(chunk)
        if collection_filter and collection != collection_filter:
            continue
        chunk_id = _chunk_id(chunk.get("doc_id", ""), chunk.get("section_ref", str(uuid.uuid4())))
        payload = _build_payload(chunk, collection)
        texts_to_embed.append(chunk["content"])
        meta_list.append((chunk_id, collection, payload))

    if not texts_to_embed:
        logger.info("No chunks to embed for filter=%s", collection_filter)
        return counts

    logger.info("Embedding %d chunks (batch_size=%d)...", len(texts_to_embed), batch_size)

    # Batch embed
    for i in range(0, len(texts_to_embed), batch_size):
        batch_texts = texts_to_embed[i : i + batch_size]
        batch_meta = meta_list[i : i + batch_size]

        vectors = await embedding_service.aembed_batch(batch_texts)

        points_batch: list[tuple[str, "PointStruct"]] = []
        for (chunk_id, collection, payload), vector in zip(batch_meta, vectors):
            from qdrant_client.models import PointStruct
            pt = PointStruct(id=chunk_id, vector=vector, payload=payload)
            points_batch.append((collection, pt))

        await _flush(points_batch)
        logger.info(
            "Progress: %d/%d embedded and upserted",
            min(i + batch_size, len(texts_to_embed)),
            len(texts_to_embed),
        )

    return counts


async def run_ingest(args: argparse.Namespace) -> None:
    """Main async ingestion flow."""
    from app.services.rag.embedding_service import EmbeddingService
    from app.services.knowledge.collection_manager import CollectionManager
    from app.core.config import settings

    # Initialise services
    embedding_service = EmbeddingService(backend="openai")
    manager = CollectionManager(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=getattr(settings, "QDRANT_API_KEY", None) or None,
    )

    # Ensure collections exist
    await ensure_collections(manager)

    if args.stats:
        stats = await manager.collection_stats()
        print("\n=== Qdrant Collection Stats ===")
        for col, info in stats.items():
            print(f"  {col}: {info}")
        return

    # Determine target collections
    target_collections = list(SEED_FILES.keys())
    if args.collection:
        if args.collection not in SEED_FILES:
            logger.error("Unknown collection: %s", args.collection)
            logger.info("Valid collections: %s", ", ".join(SEED_FILES))
            sys.exit(1)
        target_collections = [args.collection]

    if args.reset:
        for col in target_collections:
            logger.info("Resetting collection: %s", col)
            try:
                manager.client.delete_collection(col)
                logger.info("Deleted collection: %s", col)
            except Exception as e:
                logger.warning("Could not delete %s: %s", col, e)
        await ensure_collections(manager)

    # Load all seed files relevant to target collections
    all_chunks: list[dict] = []
    seen_files: set[str] = set()
    for col in target_collections:
        for fname in SEED_FILES.get(col, []):
            if fname in seen_files:
                continue
            seen_files.add(fname)
            fpath = SEED_DIR / fname
            if not fpath.exists():
                logger.warning("Seed file not found: %s — skipping", fpath)
                continue
            chunks = _load_seed_file(fpath)
            all_chunks.extend(chunks)
            logger.info("Loaded %d chunks from %s", len(chunks), fname)

    if not all_chunks:
        logger.error("No seed data found to ingest.")
        sys.exit(1)

    # Filter by target collection if specific
    col_filter = args.collection if args.collection else None

    total_counts = await ingest_seed_chunks(
        all_chunks,
        embedding_service,
        manager,
        collection_filter=col_filter,
        batch_size=args.batch_size,
    )

    print("\n=== Ingestion Complete ===")
    total = 0
    for col, count in sorted(total_counts.items()):
        print(f"  {col}: {count} chunks upserted")
        total += count
    print(f"  TOTAL: {total} chunks")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sancta Nexus — Church corpus ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        default=True,
        help="Ingest only local seed JSON files (default: True)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest seed data AND fetch remote documents (future)",
    )
    parser.add_argument(
        "--collection",
        metavar="NAME",
        help=(
            "Restrict ingestion to a single collection. "
            f"Valid: {', '.join(SEED_FILES)}"
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate target collections before ingesting",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print collection stats and exit",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        metavar="N",
        help="Number of chunks to embed per OpenAI API call (default: 16)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_ingest(args))
