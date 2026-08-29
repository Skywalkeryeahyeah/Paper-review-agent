from langgraph.graph import (
    StateGraph,
    START,
    END
)

from agent.state import (
    ReviewState
)

from agent.nodes import (
    parse_pdf_node,
    build_rag_index_node,
    analyze_paper_node,
    generate_review_node,
    evidence_check_node,
    regenerate_review_node,
    final_review_node,
    route_after_evidence
)


def create_review_graph():

    builder = StateGraph(
        ReviewState
    )

    builder.add_node(
        "parse_pdf",
        parse_pdf_node
    )

    builder.add_node(
        "build_rag_index",
        build_rag_index_node
    )

    builder.add_node(
        "analyze_paper",
        analyze_paper_node
    )

    builder.add_node(
        "generate_review",
        generate_review_node
    )

    builder.add_node(
        "evidence_check",
        evidence_check_node
    )

    builder.add_node(
        "regenerate_review",
        regenerate_review_node
    )

    builder.add_node(
        "final_review",
        final_review_node
    )

    builder.add_edge(
        START,
        "parse_pdf"
    )

    builder.add_edge(
        "parse_pdf",
        "build_rag_index"
    )

    builder.add_edge(
        "build_rag_index",
        "analyze_paper"
    )

    builder.add_edge(
        "analyze_paper",
        "generate_review"
    )

    builder.add_edge(
        "generate_review",
        "evidence_check"
    )

    builder.add_conditional_edges(
        "evidence_check",
        route_after_evidence,
        {
            "finalize":
                "final_review",

            "regenerate":
                "regenerate_review"
        }
    )

    builder.add_edge(
        "regenerate_review",
        "evidence_check"
    )

    builder.add_edge(
        "final_review",
        END
    )

    return builder.compile()


review_graph = (
    create_review_graph()
)