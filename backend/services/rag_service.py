import math
import os
import re
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    timeout=300.0,
    max_retries=2
)


EMBEDDING_MODEL = (
    os.getenv("EMBEDDING_MODEL")
    or "text-embedding-v4"
)

EMBEDDING_DIMENSIONS = int(
    os.getenv(
        "EMBEDDING_DIMENSIONS",
        "1024"
    )
)

CHUNK_SIZE = int(
    os.getenv(
        "RAG_CHUNK_SIZE",
        "1800"
    )
)

CHUNK_OVERLAP = int(
    os.getenv(
        "RAG_CHUNK_OVERLAP",
        "250"
    )
)

DEFAULT_TOP_K = int(
    os.getenv(
        "RAG_TOP_K",
        "6"
    )
)


_rag_store: dict[str, dict[str, Any]] = {}

_store_lock = Lock()


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def _find_good_cut(
    text: str,
    start: int,
    hard_end: int
) -> int:

    if hard_end >= len(text):
        return len(text)

    section = text[
        start:hard_end
    ]

    candidates = [
        section.rfind("\n\n"),
        section.rfind(". "),
        section.rfind("。"),
        section.rfind("; "),
        section.rfind("\n")
    ]

    best = max(candidates)

    minimum_position = int(
        len(section) * 0.65
    )

    if best >= minimum_position:
        return start + best + 1

    return hard_end


def split_pages_into_chunks(
    pages: list[dict[str, Any]]
) -> list[dict[str, Any]]:

    chunks = []

    for page_data in pages:

        page_number = page_data[
            "page"
        ]

        text = normalize_text(
            page_data.get(
                "text",
                ""
            )
        )

        if not text:
            continue

        start = 0
        chunk_index = 0

        while start < len(text):

            hard_end = min(
                start + CHUNK_SIZE,
                len(text)
            )

            end = _find_good_cut(
                text,
                start,
                hard_end
            )

            chunk_text = text[
                start:end
            ].strip()

            if chunk_text:

                chunks.append({
                    "id": (
                        f"p{page_number}"
                        f"_c{chunk_index}"
                    ),
                    "page":
                        page_number,
                    "chunk_index":
                        chunk_index,
                    "text":
                        chunk_text
                })

                chunk_index += 1

            if end >= len(text):
                break

            next_start = (
                end - CHUNK_OVERLAP
            )

            if next_start <= start:
                next_start = end

            start = next_start

    return chunks


def _normalize_vector(
    vector: list[float]
) -> list[float]:

    norm = math.sqrt(
        sum(
            value * value
            for value in vector
        )
    )

    if norm == 0:
        return vector

    return [
        value / norm
        for value in vector
    ]


def _embed_texts(
    texts: list[str]
) -> list[list[float]]:

    if not texts:
        return []

    batch_size = 10

    all_vectors = []

    for i in range(
        0,
        len(texts),
        batch_size
    ):

        batch = texts[
            i:i + batch_size
        ]

        response = (
            client
            .embeddings
            .create(
                model=
                    EMBEDDING_MODEL,

                input=
                    batch,

                dimensions=
                    EMBEDDING_DIMENSIONS,

                encoding_format=
                    "float"
            )
        )

        ordered = sorted(
            response.data,
            key=lambda item:
                item.index
        )

        for item in ordered:

            all_vectors.append(
                _normalize_vector(
                    item.embedding
                )
            )

    return all_vectors


def build_paper_index(
    paper_id: str,
    pages: list[dict[str, Any]]
) -> int:

    with _store_lock:

        existing = (
            _rag_store.get(
                paper_id
            )
        )

    if existing:
        return len(
            existing["chunks"]
        )

    chunks = split_pages_into_chunks(
        pages
    )

    if not chunks:
        raise ValueError(
            "无法从论文中生成 RAG Chunk"
        )

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    vectors = _embed_texts(
        texts
    )

    if len(vectors) != len(chunks):
        raise RuntimeError(
            "Embedding 数量与 Chunk 数量不一致"
        )

    with _store_lock:

        _rag_store[paper_id] = {
            "chunks":
                chunks,

            "vectors":
                vectors
        }

    return len(chunks)


def has_paper_index(
    paper_id: str
) -> bool:

    with _store_lock:
        return paper_id in _rag_store


def _tokenize(
    text: str
) -> set[str]:

    words = re.findall(
        r"[A-Za-z0-9][A-Za-z0-9_\-]{2,}",
        text.lower()
    )

    stop_words = {
        "the",
        "and",
        "that",
        "this",
        "with",
        "for",
        "from",
        "are",
        "was",
        "were",
        "have",
        "has",
        "should",
        "could",
        "would",
        "manuscript",
        "authors",
        "paper"
    }

    return {
        word
        for word in words
        if word not in stop_words
    }


def _lexical_score(
    query: str,
    text: str
) -> float:

    query_words = _tokenize(
        query
    )

    if not query_words:
        return 0.0

    text_words = _tokenize(
        text
    )

    overlap = (
        query_words
        & text_words
    )

    return (
        len(overlap)
        / len(query_words)
    )


def _dot_product(
    a: list[float],
    b: list[float]
) -> float:

    return sum(
        x * y
        for x, y in zip(a, b)
    )


def retrieve_relevant_chunks(
    paper_id: str,
    query: str,
    top_k: int | None = None
) -> list[dict[str, Any]]:

    if top_k is None:
        top_k = DEFAULT_TOP_K

    with _store_lock:

        paper_index = (
            _rag_store.get(
                paper_id
            )
        )

    if not paper_index:

        raise ValueError(
            f"论文 {paper_id} 尚未构建 RAG 索引"
        )

    query_vector = _embed_texts(
        [query]
    )[0]

    chunks = paper_index[
        "chunks"
    ]

    vectors = paper_index[
        "vectors"
    ]

    results = []

    for chunk, vector in zip(
        chunks,
        vectors
    ):

        semantic_score = (
            _dot_product(
                query_vector,
                vector
            )
        )

        lexical_score = (
            _lexical_score(
                query,
                chunk["text"]
            )
        )

        final_score = (
            semantic_score * 0.9
            +
            lexical_score * 0.1
        )

        results.append({
            **chunk,

            "semantic_score":
                semantic_score,

            "lexical_score":
                lexical_score,

            "score":
                final_score
        })

    results.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )

    return results[
        :top_k
    ]