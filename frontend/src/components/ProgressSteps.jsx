const BASE_STEPS = [
  {
    key: "upload",
    title: "上传论文",
    description: "上传 PDF 并创建论文任务"
  },
  {
    key: "parse_pdf",
    title: "解析 PDF",
    description: "提取论文全文与页码信息"
  },
  {
    key: "build_rag_index",
    title: "构建 RAG 检索索引",
    description: "切分论文并生成语义向量"
  },
  {
    key: "analyze_paper",
    title: "理解论文",
    description: "分析研究问题、方法、实验与结论"
  },
  {
    key: "generate_review",
    title: "生成审稿意见",
    description: "Reviewer Agent 生成候选意见"
  },
  {
    key: "evidence_check",
    title: "RAG 证据核验",
    description: "检索论文证据并验证候选意见"
  },
  {
    key: "final_review",
    title: "整理最终结果",
    description: "筛选并生成最终审稿报告"
  }
];


function ProgressSteps({
  phase,
  uploadDone,
  currentNode,
  completedNodes = [],
  retryCount = 0
}) {

  const normalizedCompletedNodes = completedNodes.map((node) => {
    if (
      typeof node === "string" &&
      node.startsWith("regenerate_review")
    ) {
      return "regenerate_review";
    }

    return node;
  });


  const showRegenerate =
    retryCount > 0 ||
    currentNode === "regenerate_review" ||
    normalizedCompletedNodes.includes("regenerate_review");


  const steps = [...BASE_STEPS];


  if (showRegenerate) {

    const evidenceIndex = steps.findIndex(
      (step) => step.key === "evidence_check"
    );

    steps.splice(
      evidenceIndex + 1,
      0,
      {
        key: "regenerate_review",
        title: "Agent 自我修正",
        description: "补充候选意见并重新进行证据核验"
      }
    );
  }


  const getStepStatus = (step) => {

    if (step.key === "upload") {

      if (
        uploadDone ||
        phase === "reviewing" ||
        phase === "done"
      ) {
        return "done";
      }

      if (phase === "uploading") {
        return "active";
      }

      return "waiting";
    }


    if (
      normalizedCompletedNodes.includes(
        step.key
      )
    ) {
      return "done";
    }


    /*
      整个 Agent 已经成功完成时，
      所有固定流程节点都必然已经执行完成。

      这样可以防止 SSE 最终状态同步时，
      某个节点（例如 build_rag_index）
      因 completedNodes 重建而重新显示成白色。
    */
    if (
      phase === "done" &&
      step.key !== "regenerate_review"
    ) {
      return "done";
    }


    if (currentNode === step.key) {
      return "active";
    }


    return "waiting";
  };


  return (
    <div className="progress-card">

      <div className="section-heading">

        <div className="section-number">
          02
        </div>

        <div>
          <h2>
            Agent 执行流程
          </h2>

          <p>
            LangGraph 多节点智能审稿工作流
          </p>
        </div>

      </div>


      <div className="steps">

        {steps.map((step, index) => {

          const status =
            getStepStatus(step);

          const isLast =
            index === steps.length - 1;


          return (
            <div
              className={`step ${status}`}
              key={step.key}
            >

              <div className="step-left">

                <div className="step-circle">

                  {status === "done"
                    ? "✓"
                    : index + 1}

                </div>


                {!isLast && (
                  <div className="step-line" />
                )}

              </div>


              <div className="step-content">

                <strong>
                  {step.title}
                </strong>

                <span>
                  {step.description}
                </span>


                {status === "active" && (
                  <small>
                    正在执行...
                  </small>
                )}


                {status === "done" && (
                  <small>
                    已完成
                  </small>
                )}

              </div>

            </div>
          );
        })}

      </div>

    </div>
  );
}


export default ProgressSteps;