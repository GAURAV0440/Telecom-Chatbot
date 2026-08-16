from functools import lru_cache
from pathlib import Path
import json
import re
from typing import Any

from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient

from backend.app.config import settings


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHUNKS_PATH = Path(
    "backend/data/processed/ts_36_413_chunks.json"
)

SEMANTIC_TOP_K = 15
BM25_TOP_K = 15
CANDIDATE_TOP_K = 15

MIN_SEMANTIC_SCORE = 0.68
MIN_HYBRID_SCORE = 0.55
MIN_LEXICAL_OVERLAP = 0.05

SEMANTIC_WEIGHT = 0.65
BM25_WEIGHT = 0.20
LEXICAL_WEIGHT = 0.15

TECHNICAL_PHRASE_BOOST = 0.10
EXACT_PHRASE_BOOST = 0.10


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

OUT_OF_SCOPE_TERMS = (
    "ngap",
    "ng interface",
    "5g nas",
    "5g",
    "new radio",
    "nr ",
    "physical layer",
    "phy layer",
    "mac layer",
    "rlc layer",
    "pdcp layer",
    "tcp",
    "python",
    "javascript",
    "java",
    "weather",
    "capital of",
    "prime minister",
    "president",
    "ceo of",
    "stock price",
    "bitcoin",
)


IN_SCOPE_TERMS = (
    "s1ap",
    "s1 interface",
    "s1 setup",
    "s1ap procedure",
    "s1ap message",
    "s1ap service",
    "e-rab",
    "erab",
    "e-utran",
    "e-nodeb",
    "enodeb",
    "enb",
    "mme",
    "ue-associated",
    "non ue-associated",
    "ue context",
    "ue capability",
    "signalling connection",
    "signaling connection",
    "handover preparation",
    "handover cancel",
    "initial context setup",
    "error indication",
    "paging procedure",
    "reset procedure",
)


TECHNICAL_PHRASES = (
    "e-rab setup response",
    "e-rab setup request",
    "e-rab release",
    "e-rab setup",
    "e-rab",
    "handover preparation",
    "handover cancel",
    "initial context setup",
    "error indication",
    "paging procedure",
    "s1 setup",
    "signalling connection",
    "signaling connection",
    "ue-associated services",
    "non ue-associated services",
    "s1ap services",
    "s1ap procedure",
    "s1ap message",
    "ue context",
    "ue capability",
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "been",
    "being",
    "between",
    "can",
    "could",
    "does",
    "do",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "which",
    "why",
    "with",
}


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize technical text for matching.

    E-RAB, E_RAB and E RAB become equivalent.
    """

    if not text:
        return ""

    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text: str) -> list[str]:
    """
    Tokenize technical text while preserving terms such as E-RAB.
    """

    if not text:
        return []

    return re.findall(
        r"\b[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*\b",
        text.lower(),
    )


def meaningful_tokens(text: str) -> set[str]:
    """
    Return non-stopword tokens.
    """

    return {
        token
        for token in tokenize(text)
        if token not in STOP_WORDS
    }


# ---------------------------------------------------------------------------
# Scope detection
# ---------------------------------------------------------------------------

def is_in_scope(query: str) -> bool:
    """
    Determine whether a query belongs to the indexed
    TS 36.413 / S1AP knowledge base.

    The scope gate intentionally runs before retrieval.
    """

    if not query or not query.strip():
        return False

    normalized_query = normalize_text(query)

    # Explicit rejection takes priority.
    for term in OUT_OF_SCOPE_TERMS:
        if normalize_text(term) in normalized_query:
            return False

    # Require an explicit concept belonging to the indexed standard.
    for term in IN_SCOPE_TERMS:
        if normalize_text(term) in normalized_query:
            return True

    return False


# ---------------------------------------------------------------------------
# Chunk loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_chunks() -> tuple[dict[str, Any], ...]:
    """
    Load and validate the processed document chunks once.
    """

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Processed chunks file not found: {CHUNKS_PATH}"
        )

    try:
        with CHUNKS_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            chunks = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {CHUNKS_PATH}"
        ) from exc

    if not isinstance(chunks, list) or not chunks:
        raise ValueError(
            "Processed chunks JSON must contain a non-empty list."
        )

    required_fields = {
        "chunk_id",
        "text",
        "section_path",
        "specification",
        "version",
        "release",
        "source_file",
    }

    validated_chunks: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks):

        if not isinstance(chunk, dict):
            raise ValueError(
                f"Chunk {index} must be a JSON object."
            )

        missing = required_fields.difference(chunk)

        if missing:
            raise ValueError(
                f"Chunk {index} is missing fields: "
                f"{sorted(missing)}"
            )

        if not isinstance(chunk["text"], str):
            raise ValueError(
                f"Chunk {index} has invalid 'text'."
            )

        if not chunk["text"].strip():
            continue

        validated_chunks.append(chunk)

    if not validated_chunks:
        raise ValueError(
            "No valid document chunks were found."
        )

    return tuple(validated_chunks)


# ---------------------------------------------------------------------------
# Result construction
# ---------------------------------------------------------------------------

def build_result(
    chunk: dict[str, Any],
    *,
    semantic_score: float = 0.0,
    bm25_score: float = 0.0,
) -> dict[str, Any]:
    """
    Create a consistent retrieval result.
    """

    return {
        "chunk_id": chunk["chunk_id"],
        "text": chunk["text"],
        "section_path": chunk["section_path"],
        "specification": chunk["specification"],
        "version": chunk["version"],
        "release": chunk["release"],
        "source_file": chunk["source_file"],
        "semantic_score": float(semantic_score),
        "bm25_score": float(bm25_score),
    }


# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_bm25() -> BM25Okapi:
    """
    Build the BM25 index once per application process.
    """

    chunks = load_chunks()

    corpus = [
        tokenize(
            f"{chunk['section_path']} {chunk['text']}"
        )
        for chunk in chunks
    ]

    return BM25Okapi(corpus)


def bm25_search(
    query: str,
    limit: int = BM25_TOP_K,
) -> list[dict[str, Any]]:
    """
    Retrieve candidate chunks using BM25.
    """

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    chunks = load_chunks()
    bm25 = get_bm25()

    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )[:limit]

    return [
        build_result(
            chunks[index],
            bm25_score=scores[index],
        )
        for index in ranked_indices
    ]


# ---------------------------------------------------------------------------
# Semantic retrieval
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    """
    Load the embedding model once per application process.
    """

    return TextEmbedding(
        model_name=settings.embedding_model
    )


def semantic_search(
    query: str,
    limit: int = SEMANTIC_TOP_K,
) -> list[dict[str, Any]]:
    """
    Retrieve candidate chunks using Qdrant.
    """

    embedding_model = get_embedding_model()

    query_vector = next(
        embedding_model.embed([query])
    ).tolist()

    client = QdrantClient(
        path=settings.qdrant_path
    )

    try:
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            limit=limit,
            with_payload=True,
        ).points
    finally:
        client.close()

    output: list[dict[str, Any]] = []

    for result in results:

        payload = result.payload

        if not payload:
            continue

        output.append(
            build_result(
                payload,
                semantic_score=result.score,
            )
        )

    return output


# ---------------------------------------------------------------------------
# Relevance features
# ---------------------------------------------------------------------------

def lexical_overlap(
    query: str,
    text: str,
) -> float:
    """
    Calculate meaningful query-term overlap.
    """

    query_terms = meaningful_tokens(query)
    text_terms = meaningful_tokens(text)

    if not query_terms:
        return 0.0

    return len(
        query_terms.intersection(text_terms)
    ) / len(query_terms)


def query_technical_phrases(
    query: str,
) -> list[str]:
    """
    Extract technical phrases explicitly present in the query.

    Longer phrases are preferred.
    """

    normalized_query = normalize_text(query)

    phrases = {
        normalize_text(phrase)
        for phrase in TECHNICAL_PHRASES
        if normalize_text(phrase) in normalized_query
    }

    return sorted(
        phrases,
        key=len,
        reverse=True,
    )


def technical_phrase_score(
    query: str,
    text: str,
    section_path: str,
) -> float:
    """
    Score explicit technical phrase matches.
    """

    phrases = query_technical_phrases(query)

    if not phrases:
        return 0.0

    searchable_text = normalize_text(
        f"{section_path} {text}"
    )

    matched = sum(
        phrase in searchable_text
        for phrase in phrases
    )

    return matched / len(phrases)


def has_exact_technical_match(
    query: str,
    text: str,
    section_path: str,
) -> bool:
    """
    Check whether the most specific technical phrase
    from the query exists in the retrieved evidence.
    """

    phrases = query_technical_phrases(query)

    if not phrases:
        return False

    searchable_text = normalize_text(
        f"{section_path} {text}"
    )

    return phrases[0] in searchable_text


# ---------------------------------------------------------------------------
# Hybrid retrieval
# ---------------------------------------------------------------------------

def hybrid_search(
    query: str,
    limit: int = CANDIDATE_TOP_K,
) -> list[dict[str, Any]]:
    """
    Combine semantic retrieval, BM25 and lexical relevance.
    """

    semantic_results = semantic_search(
        query,
        limit=SEMANTIC_TOP_K,
    )

    bm25_results = bm25_search(
        query,
        limit=BM25_TOP_K,
    )

    combined: dict[str, dict[str, Any]] = {}

    for result in semantic_results:
        combined[str(result["chunk_id"])] = result.copy()

    for result in bm25_results:

        chunk_id = str(result["chunk_id"])

        if chunk_id in combined:
            combined[chunk_id]["bm25_score"] = (
                result["bm25_score"]
            )
        else:
            combined[chunk_id] = result.copy()

    if not combined:
        return []

    bm25_max = max(
        (
            result["bm25_score"]
            for result in combined.values()
        ),
        default=0.0,
    )

    for result in combined.values():

        semantic_score = result["semantic_score"]

        bm25_score = (
            result["bm25_score"] / bm25_max
            if bm25_max > 0
            else 0.0
        )

        overlap = lexical_overlap(
            query,
            result["text"],
        )

        phrase_score = technical_phrase_score(
            query,
            result["text"],
            result["section_path"],
        )

        exact_match = has_exact_technical_match(
            query,
            result["text"],
            result["section_path"],
        )

        score = (
            SEMANTIC_WEIGHT * semantic_score
            + BM25_WEIGHT * bm25_score
            + LEXICAL_WEIGHT * overlap
        )

        if phrase_score > 0:
            score += TECHNICAL_PHRASE_BOOST * phrase_score

        if exact_match:
            score += EXACT_PHRASE_BOOST

        result["lexical_overlap"] = overlap
        result["technical_phrase_score"] = phrase_score
        result["hybrid_score"] = min(
            max(score, 0.0),
            1.0,
        )

    return sorted(
        combined.values(),
        key=lambda item: item["hybrid_score"],
        reverse=True,
    )[:limit]


# ---------------------------------------------------------------------------
# Final evidence selection
# ---------------------------------------------------------------------------

def get_relevant_evidence(
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Return evidence that is sufficiently relevant to the query.

    Empty list means the answer-generation layer must refuse.
    """

    if not query or not query.strip():
        return []

    if not is_in_scope(query):
        return []

    candidates = hybrid_search(
        query,
        limit=CANDIDATE_TOP_K,
    )

    evidence: list[dict[str, Any]] = []

    for result in candidates:

        semantic_score = result["semantic_score"]
        hybrid_score = result["hybrid_score"]
        overlap = result["lexical_overlap"]
        phrase_score = result["technical_phrase_score"]

        exact_match = has_exact_technical_match(
            query,
            result["text"],
            result["section_path"],
        )

        normal_match = (
            semantic_score >= MIN_SEMANTIC_SCORE
            and hybrid_score >= MIN_HYBRID_SCORE
            and overlap >= MIN_LEXICAL_OVERLAP
        )

        technical_match = (
            exact_match
            and semantic_score >= 0.60
            and hybrid_score >= 0.50
        )

        phrase_match = (
            phrase_score >= 0.50
            and semantic_score >= 0.62
            and hybrid_score >= 0.52
        )

        if (
            normal_match
            or technical_match
            or phrase_match
        ):
            evidence.append(result)

    return evidence[:limit]