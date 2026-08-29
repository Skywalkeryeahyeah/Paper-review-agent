import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from services.rag_service import (
    retrieve_relevant_chunks
)


load_dotenv()


client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    timeout=300.0,
    max_retries=2
)


MODEL = (
    os.getenv("LLM_MODEL")
    or "qwen3.7-plus"
)


EVIDENCE_SYSTEM_PROMPT = """
You are an Evidence Checker for an academic
peer-review system.

Your task is NOT to generate new reviewer
comments.

Your task is to verify whether each reviewer
comment is supported by evidence retrieved
from the manuscript.

For each reviewer comment, you will receive
several manuscript chunks retrieved by a RAG
system.

Use ONLY the retrieved manuscript evidence
as factual evidence.

The paper analysis may be used only as global
orientation and must not override the retrieved
manuscript text.

Classify each comment into exactly one of the
following states:

SUPPORTED:
The reviewer concern is clearly valid according
to the retrieved manuscript evidence.

PARTIALLY_SUPPORTED:
The manuscript addresses the topic to some
extent, but the exact requested information,
analysis, evidence, metric, explanation, or
clarification remains incomplete.

UNSUPPORTED:
The retrieved manuscript evidence clearly
shows that the reviewer's concern is incorrect
or has already been adequately addressed.

Important rules:

1. A broad mention is not enough to resolve a
specific concern.

For example, saying that cross-validation was
used does not automatically resolve a request
for actual cross-validation metrics.

2. Do NOT treat the absence of information from
the retrieved chunks alone as definitive proof
that the information is absent from the entire
manuscript.

For negative claims such as "the manuscript
does not report X", be conservative.

3. Mark a negative concern as SUPPORTED only
when the retrieved evidence covers the relevant
section/topic and the requested exact detail
still appears unresolved.

4. If the topic is partly addressed, prefer
PARTIALLY_SUPPORTED and rewrite the comment so
that it acknowledges what the manuscript already
provides.

5. Mark a concern as UNSUPPORTED only when the
retrieved evidence explicitly resolves the
concern.

6. Evidence page numbers must come only from the
retrieved chunks supplied to you.

7. Never invent evidence, page numbers, results,
experiments, methods, or manuscript content.

Return valid JSON only.
"""


def _build_evidence_packets(
    paper_id: str,
    comments: list[str]
):

    packets = []

    for index, comment in enumerate(
        comments,
        start=1
    ):

        chunks = (
            retrieve_relevant_chunks(
                paper_id=
                    paper_id,

                query=
                    comment
            )
        )

        packets.append({
            "comment_index":
                index,

            "comment":
                comment,

            "chunks":
                chunks
        })

    return packets


def _format_packets(
    packets
) -> str:

    parts = []

    for packet in packets:

        parts.append(
            (
                "\n"
                "====================\n"
                f"COMMENT "
                f"{packet['comment_index']}\n"
                "====================\n"
                f"{packet['comment']}\n"
            )
        )

        parts.append(
            "\nRETRIEVED EVIDENCE:\n"
        )

        for rank, chunk in enumerate(
            packet["chunks"],
            start=1
        ):

            parts.append(
                (
                    "\n"
                    f"[Evidence {rank} | "
                    f"Page {chunk['page']} | "
                    f"Chunk {chunk['id']} | "
                    f"Score "
                    f"{chunk['score']:.4f}]\n"
                    f"{chunk['text']}\n"
                )
            )

    return "\n".join(
        parts
    )


def check_review_evidence(
    paper_id: str,
    review: dict[str, Any],
    paper_analysis: dict[str, Any]
):

    comments = (
        review.get(
            "comments",
            []
        )
    )

    if not comments:

        return {
            "checked_comments": []
        }

    packets = (
        _build_evidence_packets(
            paper_id,
            comments
        )
    )

    evidence_text = (
        _format_packets(
            packets
        )
    )

    analysis_text = json.dumps(
        paper_analysis,
        ensure_ascii=False,
        indent=2
    )

    user_prompt = f"""
Below is a structured analysis of the paper.

This analysis is ONLY for global orientation.
The retrieved manuscript chunks are the
authoritative evidence.

PAPER ANALYSIS:
{analysis_text}


Below are reviewer comments and manuscript
evidence retrieved specifically for each
comment using semantic retrieval.

{evidence_text}


Check every reviewer comment.

Return JSON using exactly this structure:

{{
  "checked_comments": [
    {{
      "comment_index": 1,
      "original_comment": "",
      "status": "SUPPORTED",
      "confidence": 0.0,
      "evidence_pages": [],
      "evidence": "",
      "reason": "",
      "revised_comment": ""
    }}
  ]
}}

Requirements:

- status must be exactly one of:
  SUPPORTED
  PARTIALLY_SUPPORTED
  UNSUPPORTED

- confidence must be between 0 and 1.

- evidence_pages must contain only page numbers
  from the supplied retrieved chunks.

- evidence should briefly summarize the strongest
  manuscript evidence.

- reason should explain why the status was chosen.

- For PARTIALLY_SUPPORTED, revised_comment should
  contain a corrected reviewer comment that
  acknowledges what the manuscript already
  provides while retaining the unresolved concern.

- For SUPPORTED, revised_comment may be empty unless
  wording correction is useful.

- For UNSUPPORTED, revised_comment should be empty.
"""

    response = (
        client
        .chat
        .completions
        .create(
            model=MODEL,

            messages=[
                {
                    "role":
                        "system",

                    "content":
                        EVIDENCE_SYSTEM_PROMPT
                },

                {
                    "role":
                        "user",

                    "content":
                        user_prompt
                }
            ],

            temperature=0,

            response_format={
                "type":
                    "json_object"
            }
        )
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    result = json.loads(
        content
    )

    checked_comments = (
        result.get(
            "checked_comments",
            []
        )
    )

    original_comments = {
        index:
            comment

        for index, comment
        in enumerate(
            comments,
            start=1
        )
    }

    normalized_results = []

    for item in checked_comments:

        index = item.get(
            "comment_index"
        )

        original_comment = (
            original_comments.get(
                index,
                item.get(
                    "original_comment",
                    ""
                )
            )
        )

        status = (
            item.get(
                "status",
                ""
            )
            .upper()
            .strip()
        )

        if status not in {
            "SUPPORTED",
            "PARTIALLY_SUPPORTED",
            "UNSUPPORTED"
        }:

            status = (
                "PARTIALLY_SUPPORTED"
            )

        try:

            confidence = float(
                item.get(
                    "confidence",
                    0
                )
            )

        except Exception:
            confidence = 0.0

        confidence = max(
            0.0,
            min(
                confidence,
                1.0
            )
        )

        normalized_results.append({
            "original_comment":
                original_comment,

            "status":
                status,

            "confidence":
                confidence,

            "evidence_pages":
                item.get(
                    "evidence_pages",
                    []
                ),

            "evidence":
                item.get(
                    "evidence",
                    ""
                ),

            "reason":
                item.get(
                    "reason",
                    ""
                ),

            "revised_comment":
                item.get(
                    "revised_comment",
                    ""
                )
        })

    return {
        "checked_comments":
            normalized_results
    }


def build_checked_review(
    review: dict[str, Any],
    evidence_result: dict[str, Any]
):

    final_comments = []

    checked_comments = (
        evidence_result.get(
            "checked_comments",
            []
        )
    )

    for item in checked_comments:

        status = (
            item.get(
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

            final_comment = (
                revised_comment
                or original_comment
            )

            if final_comment:

                final_comments.append(
                    final_comment
                )

        elif (
            status
            == "PARTIALLY_SUPPORTED"
            and confidence >= 0.5
        ):

            final_comment = (
                revised_comment
                or original_comment
            )

            if final_comment:

                final_comments.append(
                    final_comment
                )

    return {
        "overall_review":
            review.get(
                "overall_review",
                ""
            ),

        "comments":
            final_comments,

        "recommendation":
            review.get(
                "recommendation",
                ""
            )
    }