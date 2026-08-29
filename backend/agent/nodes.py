from typing import Literal

from langgraph.config import (
    get_stream_writer
)

from agent.state import (
    ReviewState
)

from services.pdf_service import (
    parse_pdf
)

from services.llm_service import (
    analyze_paper
)

from services.review_service import (
    generate_review,
    generate_additional_comments,
    format_review
)

from services.evidence_service import (
    check_review_evidence,
    build_checked_review
)

from services.rag_service import (
    build_paper_index
)


MIN_FINAL_COMMENTS = 4

TARGET_FINAL_COMMENTS = 5


def emit_progress(
    node: str,
    message: str,
    retry_count: int = 0
):

    try:

        writer = (
            get_stream_writer()
        )

        writer({
            "node":
                node,

            "status":
                "running",

            "message":
                message,

            "retry_count":
                retry_count
        })

    except Exception:
        pass


def parse_pdf_node(
    state: ReviewState
):

    emit_progress(
        node="parse_pdf",
        message=(
            "正在解析 PDF "
            "并提取论文文本..."
        )
    )

    result = parse_pdf(
        state["file_path"]
    )

    return {
        "page_count":
            result["page_count"],

        "pages":
            result["pages"],

        "trace": [
            "parse_pdf"
        ]
    }


def build_rag_index_node(
    state: ReviewState
):

    emit_progress(
        node="build_rag_index",
        message=(
            "正在切分论文并构建 "
            "RAG 向量检索索引..."
        )
    )

    chunk_count = (
        build_paper_index(
            paper_id=
                state["paper_id"],

            pages=
                state["pages"]
        )
    )

    return {
        "rag_ready":
            True,

        "rag_chunk_count":
            chunk_count,

        "trace": [
            "build_rag_index"
        ]
    }


def analyze_paper_node(
    state: ReviewState
):

    emit_progress(
        node="analyze_paper",
        message=(
            "正在理解论文研究问题、"
            "方法、实验与主要结论..."
        )
    )

    analysis = analyze_paper(
        state["pages"]
    )

    return {
        "analysis":
            analysis,

        "trace": [
            "analyze_paper"
        ]
    }


def generate_review_node(
    state: ReviewState
):

    emit_progress(
        node="generate_review",
        message=(
            "Reviewer Agent "
            "正在生成候选审稿意见..."
        )
    )

    review = generate_review(
        state["analysis"],
        state["pages"]
    )

    return {
        "raw_review":
            review,

        "trace": [
            "generate_review"
        ]
    }


def evidence_check_node(
    state: ReviewState
):

    retry_count = (
        state.get(
            "retry_count",
            0
        )
    )

    if retry_count == 0:

        message = (
            "Evidence Checker "
            "正在通过 RAG 检索论文证据..."
        )

    else:

        message = (
            f"Evidence Checker "
            f"正在进行第 "
            f"{retry_count + 1} "
            f"轮 RAG 证据核验..."
        )

    emit_progress(
        node="evidence_check",
        message=message,
        retry_count=retry_count
    )

    evidence_result = (
        check_review_evidence(
            paper_id=
                state["paper_id"],

            review=
                state["raw_review"],

            paper_analysis=
                state["analysis"]
        )
    )

    return {
        "evidence_result":
            evidence_result,

        "trace": [
            "evidence_check"
        ]
    }


def _get_valid_comments(
    evidence_result
):

    valid_comments = []

    checked_comments = (
        evidence_result.get(
            "checked_comments",
            []
        )
    )

    for item in checked_comments:

        status = (
            item
            .get(
                "status",
                ""
            )
            .upper()
        )

        confidence = float(
            item.get(
                "confidence",
                0
            )
        )

        original_comment = (
            item.get(
                "original_comment",
                ""
            )
            .strip()
        )

        revised_comment = (
            item.get(
                "revised_comment",
                ""
            )
            .strip()
        )

        if (
            status == "SUPPORTED"
            and confidence >= 0.6
        ):

            comment = (
                revised_comment
                or original_comment
            )

            if comment:
                valid_comments.append(
                    comment
                )

        elif (
            status
            == "PARTIALLY_SUPPORTED"
            and confidence >= 0.5
        ):

            comment = (
                revised_comment
                or original_comment
            )

            if comment:
                valid_comments.append(
                    comment
                )

    return valid_comments


def route_after_evidence(
    state: ReviewState
) -> Literal[
    "finalize",
    "regenerate"
]:

    valid_comments = (
        _get_valid_comments(
            state[
                "evidence_result"
            ]
        )
    )

    valid_count = len(
        valid_comments
    )

    retry_count = (
        state.get(
            "retry_count",
            0
        )
    )

    max_retries = (
        state.get(
            "max_retries",
            2
        )
    )

    if (
        valid_count
        >= MIN_FINAL_COMMENTS
    ):
        return "finalize"

    if (
        retry_count
        >= max_retries
    ):
        return "finalize"

    return "regenerate"


def regenerate_review_node(
    state: ReviewState
):

    current_retry = (
        state.get(
            "retry_count",
            0
        )
    )

    next_retry = (
        current_retry + 1
    )

    valid_comments = (
        _get_valid_comments(
            state[
                "evidence_result"
            ]
        )
    )

    previous_comments = (
        state[
            "raw_review"
        ]
        .get(
            "comments",
            []
        )
    )

    valid_count = len(
        valid_comments
    )

    needed_count = max(
        2,
        (
            TARGET_FINAL_COMMENTS
            - valid_count
            + 1
        )
    )

    needed_count = min(
        needed_count,
        4
    )

    emit_progress(
        node="regenerate_review",
        message=(
            f"有效意见仅 "
            f"{valid_count} 条，"
            f"正在进行第 "
            f"{next_retry} 次"
            f"自我修正..."
        ),
        retry_count=next_retry
    )

    generated = (
        generate_additional_comments(
            paper_analysis=
                state["analysis"],

            pages=
                state["pages"],

            valid_comments=
                valid_comments,

            previous_comments=
                previous_comments,

            needed_count=
                needed_count
        )
    )

    if isinstance(
        generated,
        dict
    ):

        new_comments = (
            generated.get(
                "comments",
                []
            )
        )

    else:
        new_comments = generated

    merged_comments = []

    seen = set()

    for comment in (
        valid_comments
        + new_comments
    ):

        if not isinstance(
            comment,
            str
        ):
            continue

        cleaned = (
            comment.strip()
        )

        normalized = (
            " ".join(
                cleaned
                .lower()
                .split()
            )
        )

        if (
            cleaned
            and normalized
            not in seen
        ):

            seen.add(
                normalized
            )

            merged_comments.append(
                cleaned
            )

    new_review = dict(
        state[
            "raw_review"
        ]
    )

    new_review[
        "comments"
    ] = merged_comments

    return {
        "raw_review":
            new_review,

        "retry_count":
            next_retry,

        "trace": [
            (
                "regenerate_review_"
                f"{next_retry}"
            )
        ]
    }


def final_review_node(
    state: ReviewState
):

    emit_progress(
        node="final_review",
        message=(
            "正在整理最终审稿报告..."
        ),
        retry_count=
            state.get(
                "retry_count",
                0
            )
    )

    final_review = (
        build_checked_review(
            state["raw_review"],
            state[
                "evidence_result"
            ]
        )
    )

    formatted_review = (
        format_review(
            final_review
        )
    )

    return {
        "final_review":
            final_review,

        "formatted_review":
            formatted_review,

        "trace": [
            "final_review"
        ]
    }