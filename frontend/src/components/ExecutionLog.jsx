function formatTime(timestamp) {
  if (!timestamp) {
    return "--:--:--";
  }

  const date = new Date(timestamp);

  return date.toLocaleTimeString(
    "zh-CN",
    {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    }
  );
}


function formatDuration(duration) {
  if (
    duration === undefined ||
    duration === null
  ) {
    return null;
  }

  if (duration < 1000) {
    return `${duration} ms`;
  }

  return `${(duration / 1000).toFixed(1)} s`;
}


function getNodeLabel(node) {

  const labels = {

    start:
      "Agent Started",

    parse_pdf:
      "PDF Parser",

    analyze_paper:
      "Paper Analyzer",

    generate_review:
      "Reviewer Agent",

    evidence_check:
      "Evidence Checker",

    regenerate_review:
      "Review Regenerator",

    final_review:
      "Final Review"

  };

  return (
    labels[node] ||
    node ||
    "Agent"
  );
}


function getStatusLabel(status) {

  if (status === "completed") {
    return "Completed";
  }

  if (status === "running") {
    return "Running";
  }

  if (status === "error") {
    return "Error";
  }

  return status;
}


export default function ExecutionLog({
  logs,
  running
}) {

  if (
    (!logs || logs.length === 0) &&
    !running
  ) {
    return null;
  }


  return (
    <section className="execution-log-card">

      <div className="execution-log-header">

        <div>

          <span className="execution-eyebrow">
            REAL-TIME TRACE
          </span>

          <h2>
            Agent Execution Log
          </h2>

          <p>
            LangGraph 节点实时执行记录与耗时
          </p>

        </div>


        <div
          className={
            `execution-status ${
              running
                ? "running"
                : "finished"
            }`
          }
        >

          <span />

          {running
            ? "Live"
            : "Completed"}

        </div>

      </div>


      <div className="log-timeline">

        {logs.map(
          (log, index) => {

            const isLast =
              index ===
              logs.length - 1;


            return (
              <div
                className="log-row"
                key={log.id}
              >

                <div className="log-time">

                  {formatTime(
                    log.timestamp
                  )}

                </div>


                <div className="log-marker-column">

                  <div
                    className={
                      `log-marker ${log.status}`
                    }
                  >

                    {log.status ===
                    "completed"
                      ? "✓"
                      : log.status ===
                        "error"
                        ? "!"
                        : ""}

                  </div>


                  {!isLast && (
                    <div
                      className="log-connector"
                    />
                  )}

                </div>


                <div className="log-content">

                  <div className="log-main-row">

                    <div>

                      <strong>
                        {getNodeLabel(
                          log.node
                        )}
                      </strong>


                      <span
                        className={
                          `log-status-text ${log.status}`
                        }
                      >

                        {getStatusLabel(
                          log.status
                        )}

                      </span>

                    </div>


                    {formatDuration(
                      log.duration
                    ) && (

                      <code
                        className="log-duration"
                      >
                        {formatDuration(
                          log.duration
                        )}
                      </code>

                    )}

                  </div>


                  <p>
                    {log.message}
                  </p>


                  {typeof log.retryCount ===
                    "number" &&
                    log.retryCount > 0 && (

                    <span className="retry-chip">
                      Retry {log.retryCount}
                    </span>

                  )}

                </div>

              </div>
            );
          }
        )}

      </div>


      {running && (

        <div className="execution-footer">

          <div className="mini-spinner" />

          <span>
            Agent is still running...
          </span>

        </div>

      )}

    </section>
  );
}