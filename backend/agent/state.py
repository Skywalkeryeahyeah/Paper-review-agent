from operator import add
from typing import Annotated, Any

from typing_extensions import TypedDict


class ReviewState(
    TypedDict,
    total=False
):
    paper_id: str

    file_path: str

    page_count: int

    pages: list[
        dict[str, Any]
    ]

    rag_ready: bool

    rag_chunk_count: int

    analysis: dict[
        str,
        Any
    ]

    raw_review: dict[
        str,
        Any
    ]

    evidence_result: dict[
        str,
        Any
    ]

    final_review: dict[
        str,
        Any
    ]

    formatted_review: str

    retry_count: int

    max_retries: int

    trace: Annotated[
        list[str],
        add
    ]