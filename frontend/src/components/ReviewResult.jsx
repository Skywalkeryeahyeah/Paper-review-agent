import { useState } from "react";


export default function ReviewResult({
  result
}) {

  const [copied, setCopied] =
    useState(false);

  if (!result) {
    return null;
  }


  async function handleCopy() {

    const text =
      result.formatted_review || "";

    try {

      await navigator.clipboard.writeText(
        text
      );

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 1500);

    } catch {

      alert("复制失败，请手动复制");

    }
  }


  const trace =
    result.graph_trace || [];


  return (
    <section className="result-section">

      <div className="result-header">

        <div>

          <span className="result-label">
            REVIEW RESULT
          </span>

          <h2>
            AI Peer Review
          </h2>

        </div>

        <button
          className="copy-button"
          onClick={handleCopy}
        >
          {copied
            ? "已复制 ✓"
            : "复制审稿意见"}
        </button>

      </div>


      <div className="result-stats">

        <div className="stat">

          <span>
            PDF Pages
          </span>

          <strong>
            {result.page_count ?? "-"}
          </strong>

        </div>


        <div className="stat">

          <span>
            Final Comments
          </span>

          <strong>
            {result.final_comment_count ?? "-"}
          </strong>

        </div>


        <div className="stat">

          <span>
            Retry Count
          </span>

          <strong>
            {result.retry_count ?? 0}
          </strong>

        </div>

      </div>


      {trace.length > 0 && (
        <div className="trace-box">

          <span className="trace-title">
            LangGraph Trace
          </span>

          <div className="trace-list">

            {trace.map(
              (node, index) => (

                <div
                  className="trace-node"
                  key={`${node}-${index}`}
                >

                  <span>
                    {node}
                  </span>

                  {index <
                    trace.length - 1 && (
                    <b>→</b>
                  )}

                </div>

              )
            )}

          </div>

        </div>
      )}


      <article className="review-content">
        {result.formatted_review}
      </article>

    </section>
  );
}