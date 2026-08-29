import {
  useEffect,
  useRef,
  useState
} from "react";

import "./App.css";

import {
  uploadPaper,
  createReviewStream
} from "./api/reviewApi";

import UploadPanel
  from "./components/UploadPanel";

import ProgressSteps
  from "./components/ProgressSteps";

import ReviewResult
  from "./components/ReviewResult";


const NODE_LABELS = {
  start: "LangGraph Agent",
  upload: "PDF Upload",
  parse_pdf: "PDF Parser",
  build_rag_index: "RAG Indexer",
  analyze_paper: "Paper Analyzer",
  generate_review: "Reviewer Agent",
  evidence_check: "Evidence Checker",
  regenerate_review: "Review Regenerator",
  final_review: "Final Review"
};


function formatLogTime(timestamp) {

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
    return "";
  }

  if (duration < 1000) {
    return `${duration} ms`;
  }

  return `${(duration / 1000).toFixed(1)} s`;
}


function App() {

  const [file, setFile] =
    useState(null);

  const [phase, setPhase] =
    useState("idle");

  const [
    uploadInfo,
    setUploadInfo
  ] = useState(null);

  const [
    result,
    setResult
  ] = useState(null);

  const [
    error,
    setError
  ] = useState("");

  const [
    currentNode,
    setCurrentNode
  ] = useState(null);

  const [
    completedNodes,
    setCompletedNodes
  ] = useState([]);

  const [
    progressMessage,
    setProgressMessage
  ] = useState("");

  const [
    liveRetryCount,
    setLiveRetryCount
  ] = useState(0);

  const [
    executionLogs,
    setExecutionLogs
  ] = useState([]);


  const eventSourceRef =
    useRef(null);

  const nodeStartTimesRef =
    useRef({});

  const logViewportRef =
    useRef(null);

  const autoScrollRef =
    useRef(true);


  const loading =
    phase === "uploading" ||
    phase === "reviewing";


  useEffect(() => {

    return () => {

      eventSourceRef
        .current
        ?.close();

    };

  }, []);


  useEffect(() => {

    const element =
      logViewportRef.current;

    if (
      !element ||
      !autoScrollRef.current
    ) {
      return;
    }

    element.scrollTop =
      element.scrollHeight;

  }, [executionLogs]);


  function handleLogScroll() {

    const element =
      logViewportRef.current;

    if (!element) {
      return;
    }

    const distanceFromBottom =
      element.scrollHeight -
      element.scrollTop -
      element.clientHeight;

    autoScrollRef.current =
      distanceFromBottom < 30;
  }


  function resetAgentState() {

    setCurrentNode(null);

    setCompletedNodes([]);

    setProgressMessage("");

    setLiveRetryCount(0);

    setExecutionLogs([]);

    nodeStartTimesRef.current = {};

    autoScrollRef.current = true;
  }


  function addExecutionLog({
    node,
    status,
    message,
    retryCount
  }) {

    const now =
      Date.now();

    let duration =
      null;


    if (
      status === "running" &&
      node &&
      node !== "start"
    ) {

      nodeStartTimesRef.current[
        node
      ] = now;
    }


    if (
      status === "completed" &&
      node
    ) {

      const startedAt =
        nodeStartTimesRef.current[
          node
        ];

      if (startedAt) {

        duration =
          now - startedAt;
      }
    }


    setExecutionLogs(
      previous => [

        ...previous,

        {
          id:
            `${node}-${status}-${now}-${Math.random()}`,

          node,

          status,

          message,

          retryCount,

          timestamp:
            now,

          duration
        }

      ]
    );
  }


  function handleFileChange(
    selectedFile
  ) {

    eventSourceRef
      .current
      ?.close();

    eventSourceRef.current =
      null;

    setFile(
      selectedFile
    );

    setResult(
      null
    );

    setUploadInfo(
      null
    );

    setError(
      ""
    );

    setPhase(
      "idle"
    );

    resetAgentState();
  }


  function addCompletedNode(
    node
  ) {

    if (
      !node ||
      node === "start"
    ) {
      return;
    }


    setCompletedNodes(
      previous => {

        if (
          previous.includes(
            node
          )
        ) {
          return previous;
        }

        return [
          ...previous,
          node
        ];
      }
    );
  }


  async function handleStart() {

    if (!file) {
      return;
    }


    eventSourceRef
      .current
      ?.close();

    resetAgentState();


    try {

      setError("");

      setResult(null);

      setPhase(
        "uploading"
      );

      setProgressMessage(
        "正在上传论文 PDF..."
      );


      const uploadStart =
        Date.now();


      addExecutionLog({
        node: "upload",
        status: "running",
        message: "正在上传论文 PDF..."
      });


      const uploadResult =
        await uploadPaper(
          file
        );


      const uploadDuration =
        Date.now() -
        uploadStart;


      setExecutionLogs(
        previous => [

          ...previous,

          {
            id:
              `upload-completed-${Date.now()}`,

            node:
              "upload",

            status:
              "completed",

            message:
              `PDF 上传完成，共 ${uploadResult.page_count} 页`,

            timestamp:
              Date.now(),

            duration:
              uploadDuration
          }

        ]
      );


      setUploadInfo(
        uploadResult
      );


      setPhase(
        "reviewing"
      );

      setProgressMessage(
        "正在启动 LangGraph Agent..."
      );


      const source =
        createReviewStream(

          uploadResult.paper_id,

          {

            onProgress:
              data => {

                const {
                  node,
                  status,
                  message,
                  retry_count
                } = data;


                if (message) {

                  setProgressMessage(
                    message
                  );
                }


                if (
                  typeof retry_count ===
                  "number"
                ) {

                  setLiveRetryCount(
                    retry_count
                  );
                }


                addExecutionLog({

                  node,

                  status,

                  message:
                    message ||
                    `${node} ${status}`,

                  retryCount:
                    retry_count
                });


                if (
                  status === "running" &&
                  node !== "start"
                ) {

                  setCurrentNode(
                    node
                  );
                }


                if (
                  status === "completed"
                ) {

                  addCompletedNode(
                    node
                  );

                  setCurrentNode(
                    current =>
                      current === node
                        ? null
                        : current
                  );
                }
              },


            onResult:
              data => {

                setResult(
                  data
                );

                setLiveRetryCount(
                  data.retry_count || 0
                );

                setCurrentNode(
                  null
                );

                setCompletedNodes([
                  "parse_pdf",
                  "analyze_paper",
                  "generate_review",
                  "evidence_check",
                  "final_review",

                  ...(data.retry_count > 0
                    ? [
                        "regenerate_review"
                      ]
                    : [])
                ]);


                setProgressMessage(
                  "审稿完成"
                );

                setPhase(
                  "done"
                );


                setExecutionLogs(
                  previous => [

                    ...previous,

                    {
                      id:
                        `agent-finished-${Date.now()}`,

                      node:
                        "agent",

                      status:
                        "completed",

                      message:
                        `审稿完成，共生成 ${data.final_comment_count} 条最终意见`,

                      timestamp:
                        Date.now(),

                      duration:
                        null
                    }

                  ]
                );


                eventSourceRef.current =
                  null;
              },


            onAgentError:
              message => {

                addExecutionLog({
                  node: "agent",
                  status: "error",
                  message
                });

                setError(
                  message
                );

                setCurrentNode(
                  null
                );

                setPhase(
                  "error"
                );

                eventSourceRef.current =
                  null;
              },


            onConnectionError:
              message => {

                addExecutionLog({
                  node: "connection",
                  status: "error",
                  message
                });

                setError(
                  message
                );

                setCurrentNode(
                  null
                );

                setPhase(
                  "error"
                );

                eventSourceRef.current =
                  null;
              }

          }
        );


      eventSourceRef.current =
        source;


    } catch (err) {

      console.error(err);


      addExecutionLog({
        node: "frontend",
        status: "error",
        message:
          err.message ||
          "系统发生未知错误"
      });


      setError(
        err.message ||
        "系统发生未知错误"
      );

      setCurrentNode(
        null
      );

      setPhase(
        "error"
      );
    }
  }


  function handleReset() {

    eventSourceRef
      .current
      ?.close();

    eventSourceRef.current =
      null;

    setFile(null);

    setPhase("idle");

    setUploadInfo(null);

    setResult(null);

    setError("");

    resetAgentState();
  }


  return (
    <div className="app">

      <header className="topbar">

        <div className="brand">

          <div className="brand-mark">
            PR
          </div>

          <div>

            <strong>
              Paper Reviewer
            </strong>

            <span>
              Academic Review Agent
            </span>

          </div>

        </div>


        <div className="agent-badge">

          <span
            className={
              `agent-dot ${
                loading
                  ? "running"
                  : ""
              }`
            }
          />

          {loading
            ? "Agent Running"
            : "LangGraph Agent"}

        </div>

      </header>


      <main className="main-container">

        <section className="hero">

          <span className="eyebrow">
            AI-POWERED PEER REVIEW
          </span>

          <h1>
            Academic Paper
            <br />
            Review Agent
          </h1>

          <p>
            上传学术论文，由 AI Agent
            自动完成论文理解、审稿意见生成、
            证据核验与最终审稿报告整理。
          </p>

        </section>


        <div
          className={
            `workspace ${
              uploadInfo
                ? "has-paper-info"
                : ""
            }`
          }
        >

          <div className="left-column">

            <UploadPanel
              file={file}
              onFileChange={
                handleFileChange
              }
              onStart={
                handleStart
              }
              loading={
                loading
              }
            />


            {uploadInfo && (

              <div className="paper-info-card">

                <span>
                  Paper ID
                </span>

                <code>
                  {uploadInfo.paper_id}
                </code>

                <span>
                  Pages
                </span>

                <strong>
                  {uploadInfo.page_count}
                </strong>

              </div>
            )}

          </div>


          <ProgressSteps

            phase={phase}

            uploadDone={
              Boolean(
                uploadInfo
              )
            }

            currentNode={
              currentNode
            }

            completedNodes={
              completedNodes
            }

            retryCount={
              liveRetryCount
            }

          />

        </div>


        {loading && (

          <div className="running-card">

            <div className="running-card-left">

              <div className="spinner" />

            </div>


            <div className="running-content">

              <div className="running-top">

                <div>

                  <strong>
                    Agent 正在处理论文
                  </strong>

                  <p>
                    {progressMessage ||
                      "正在处理..."}
                  </p>

                </div>


                <div className="running-node">

                  <span className="running-node-dot" />

                  {currentNode
                    ? NODE_LABELS[currentNode] ||
                      currentNode
                    : "LangGraph"}

                </div>

              </div>


              <div className="inline-trace-header">

                <span>
                  REAL-TIME TRACE
                </span>

                <small>
                  可滚动查看执行记录
                </small>

              </div>


              <div
                className="inline-trace-viewport"
                ref={
                  logViewportRef
                }
                onScroll={
                  handleLogScroll
                }
              >

                {executionLogs.map(
                  log => (

                    <div
                      className={
                        `inline-log-row ${log.status}`
                      }
                      key={log.id}
                    >

                      <span className="inline-log-time">

                        {formatLogTime(
                          log.timestamp
                        )}

                      </span>


                      <span
                        className={
                          `inline-log-indicator ${log.status}`
                        }
                      >

                        {log.status ===
                        "completed"
                          ? "✓"
                          : log.status ===
                            "error"
                            ? "!"
                            : "•"}

                      </span>


                      <span className="inline-log-node">

                        {NODE_LABELS[
                          log.node
                        ] ||
                          log.node ||
                          "Agent"}

                      </span>


                      <span className="inline-log-message">

                        {log.message}

                      </span>


                      {formatDuration(
                        log.duration
                      ) && (

                        <span className="inline-log-duration">

                          {formatDuration(
                            log.duration
                          )}

                        </span>
                      )}

                    </div>

                  )
                )}

              </div>

            </div>

          </div>

        )}


        {error && (

          <div className="error-card">

            <strong>
              请求失败
            </strong>

            <span>
              {error}
            </span>

          </div>

        )}


        <ReviewResult
          result={result}
        />


        {(result || error) && (

          <button
            className="reset-button"
            onClick={
              handleReset
            }
          >
            重新审稿
          </button>

        )}

      </main>

    </div>
  );
}


export default App;