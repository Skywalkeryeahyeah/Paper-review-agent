from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from fastapi.responses import (
    StreamingResponse
)

from services.pdf_service import (
    parse_pdf
)

from services.llm_service import (
    analyze_paper
)

from agent.graph import (
    review_graph
)

import os
import uuid
import json

from uuid import UUID


app = FastAPI(
    title="AI Paper Reviewer",
    description="AI 论文智能审稿系统后端",
    version="3.0.0"
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)


os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


NODE_COMPLETE_MESSAGES = {

    "parse_pdf":
        "PDF 解析完成",

    "build_rag_index":
        "RAG 论文检索索引构建完成",

    "analyze_paper":
        "论文理解完成",

    "generate_review":
        "候选审稿意见生成完成",

    "evidence_check":
        "审稿意见证据核验完成",

    "regenerate_review":
        "补充审稿意见生成完成",

    "final_review":
        "最终审稿报告生成完成"
}


def build_review_response(
    result: dict,
    paper_id: str
):

    evidence_result = result.get(
        "evidence_result",
        {}
    )

    final_review = result.get(
        "final_review",
        {}
    )

    return {

        "success":
            True,

        "paper_id":
            paper_id,

        "page_count":
            result.get(
                "page_count"
            ),

        "retry_count":
            result.get(
                "retry_count",
                0
            ),

        "graph_trace":
            result.get(
                "trace",
                []
            ),

        "analysis":
            result.get(
                "analysis"
            ),

        "raw_review":
            result.get(
                "raw_review"
            ),

        "evidence_check":
            evidence_result.get(
                "checked_comments",
                []
            ),

        "final_comment_count":
            len(
                final_review.get(
                    "comments",
                    []
                )
            ),

        "review":
            final_review,

        "formatted_review":
            result.get(
                "formatted_review"
            )
    }


def encode_sse_event(
    event: str,
    data: dict
):

    payload = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return (
        f"event: {event}\n"
        f"data: {payload}\n\n"
    )


def merge_state_update(
    runtime_state: dict,
    update: dict
):

    for key, value in update.items():

        if key == "trace":

            old_trace = runtime_state.get(
                "trace",
                []
            )

            runtime_state[
                "trace"
            ] = (
                old_trace
                + value
            )

        else:

            runtime_state[
                key
            ] = value


@app.get("/")
def root():

    return {
        "message":
            "AI Paper Reviewer Backend is running",

        "version":
            "3.0.0",

        "agent":
            "LangGraph",

        "streaming":
            "SSE"
    }


@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="文件名不能为空"
        )

    if not file.filename.lower().endswith(
        ".pdf"
    ):

        raise HTTPException(
            status_code=400,
            detail="只能上传 PDF 文件"
        )

    paper_id = str(
        uuid.uuid4()
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        f"{paper_id}.pdf"
    )

    content = await file.read()

    with open(
        file_path,
        "wb"
    ) as f:

        f.write(
            content
        )

    try:

        result = parse_pdf(
            file_path
        )

    except Exception as e:

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

        raise HTTPException(
            status_code=500,
            detail=f"PDF解析失败: {str(e)}"
        )

    return {
        "success":
            True,

        "paper_id":
            paper_id,

        "filename":
            file.filename,

        "page_count":
            result["page_count"]
    }


@app.post(
    "/papers/{paper_id}/analyze"
)
def analyze_uploaded_paper(
    paper_id: UUID
):

    paper_id = str(
        paper_id
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        f"{paper_id}.pdf"
    )

    if not os.path.exists(
        file_path
    ):

        raise HTTPException(
            status_code=404,
            detail="论文不存在"
        )

    try:

        pdf_result = parse_pdf(
            file_path
        )

        analysis = analyze_paper(
            pdf_result["pages"]
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"论文分析失败: {str(e)}"
        )

    return {
        "success":
            True,

        "paper_id":
            paper_id,

        "page_count":
            pdf_result["page_count"],

        "analysis":
            analysis
    }


@app.post(
    "/papers/{paper_id}/review"
)
def review_uploaded_paper(
    paper_id: UUID
):

    paper_id = str(
        paper_id
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        f"{paper_id}.pdf"
    )

    if not os.path.exists(
        file_path
    ):

        raise HTTPException(
            status_code=404,
            detail="论文不存在"
        )

    try:

        initial_state = {

            "paper_id":
                paper_id,

            "file_path":
                file_path,

            "retry_count":
                0,

            "max_retries":
                2,

            "trace":
                []
        }

        result = review_graph.invoke(
            initial_state,

            {
                "recursion_limit":
                    20
            }
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Agent审稿失败: {str(e)}"
        )

    return build_review_response(
        result,
        paper_id
    )


@app.get(
    "/papers/{paper_id}/review/stream"
)
def stream_review_uploaded_paper(
    paper_id: UUID
):

    paper_id = str(
        paper_id
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        f"{paper_id}.pdf"
    )

    if not os.path.exists(
        file_path
    ):

        raise HTTPException(
            status_code=404,
            detail="论文不存在"
        )


    def event_generator():

        initial_state = {

            "paper_id":
                paper_id,

            "file_path":
                file_path,

            "retry_count":
                0,

            "max_retries":
                2,

            "trace":
                []
        }


        runtime_state = dict(
            initial_state
        )


        yield encode_sse_event(
            "progress",
            {
                "node":
                    "start",

                "status":
                    "running",

                "message":
                    "LangGraph Agent 已启动",

                "trace":
                    [],

                "retry_count":
                    0
            }
        )


        try:

            stream = review_graph.stream(

                initial_state,

                {
                    "recursion_limit":
                        20
                },

                stream_mode=[
                    "custom",
                    "updates"
                ],

                version="v2"
            )


            for part in stream:

                part_type = part.get(
                    "type"
                )

                data = part.get(
                    "data"
                )


                if part_type == "custom":

                    if not isinstance(
                        data,
                        dict
                    ):
                        continue

                    payload = {
                        **data,

                        "trace":
                            runtime_state.get(
                                "trace",
                                []
                            ),

                        "retry_count":
                            data.get(
                                "retry_count",
                                runtime_state.get(
                                    "retry_count",
                                    0
                                )
                            )
                    }

                    yield encode_sse_event(
                        "progress",
                        payload
                    )


                elif part_type == "updates":

                    if not isinstance(
                        data,
                        dict
                    ):
                        continue


                    for (
                        node_name,
                        update
                    ) in data.items():

                        if not isinstance(
                            update,
                            dict
                        ):
                            continue


                        merge_state_update(
                            runtime_state,
                            update
                        )


                        payload = {

                            "node":
                                node_name,

                            "status":
                                "completed",

                            "message":
                                NODE_COMPLETE_MESSAGES.get(
                                    node_name,
                                    f"{node_name} 执行完成"
                                ),

                            "trace":
                                runtime_state.get(
                                    "trace",
                                    []
                                ),

                            "retry_count":
                                runtime_state.get(
                                    "retry_count",
                                    0
                                )
                        }


                        yield encode_sse_event(
                            "progress",
                            payload
                        )


            final_result = (
                build_review_response(
                    runtime_state,
                    paper_id
                )
            )


            yield encode_sse_event(
                "result",
                final_result
            )


        except Exception as e:

            yield encode_sse_event(
                "agent_error",
                {
                    "message":
                        f"Agent审稿失败: {str(e)}"
                }
            )


    return StreamingResponse(

        event_generator(),

        media_type="text/event-stream",

        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no"
        }
    )