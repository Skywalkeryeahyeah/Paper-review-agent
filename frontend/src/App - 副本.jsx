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
    liveTrace,
    setLiveTrace
  ] = useState([]);


  const [
    progressMessage,
    setProgressMessage
  ] = useState("");


  const [
    liveRetryCount,
    setLiveRetryCount
  ] = useState(0);


  const eventSourceRef =
    useRef(null);


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


  function resetAgentState() {

    setCurrentNode(
      null
    );

    setCompletedNodes(
      []
    );

    setLiveTrace(
      []
    );

    setProgressMessage(
      ""
    );

    setLiveRetryCount(
      0
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
      (previous) => {

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

      setError(
        ""
      );

      setResult(
        null
      );


      setPhase(
        "uploading"
      );


      setProgressMessage(
        "正在上传 PDF..."
      );


      const uploadResult =
        await uploadPaper(
          file
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
              (data) => {

                const {
                  node,
                  status,
                  message,
                  trace,
                  retry_count
                } = data;


                if (message) {

                  setProgressMessage(
                    message
                  );

                }


                if (
                  Array.isArray(
                    trace
                  )
                ) {

                  setLiveTrace(
                    trace
                  );

                }


                if (
                  typeof retry_count
                    === "number"
                ) {

                  setLiveRetryCount(
                    retry_count
                  );

                }


                if (
                  status ===
                  "running"
                ) {

                  if (
                    node !== "start"
                  ) {

                    setCurrentNode(
                      node
                    );

                  }

                }


                if (
                  status ===
                  "completed"
                ) {

                  addCompletedNode(
                    node
                  );


                  setCurrentNode(
                    (current) =>
                      current === node
                        ? null
                        : current
                  );

                }

              },


            onResult:
              (data) => {

                setResult(
                  data
                );


                setLiveTrace(
                  data.graph_trace ||
                  []
                );


                setLiveRetryCount(
                  data.retry_count ||
                  0
                );


                setCurrentNode(
                  null
                );


                setCompletedNodes(
                  [
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
                  ]
                );


                setProgressMessage(
                  "审稿完成"
                );


                setPhase(
                  "done"
                );


                eventSourceRef.current =
                  null;

              },


            onAgentError:
              (message) => {

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
              (message) => {

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

      console.error(
        err
      );


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


    setFile(
      null
    );

    setPhase(
      "idle"
    );

    setUploadInfo(
      null
    );

    setResult(
      null
    );

    setError(
      ""
    );


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


        <div className="workspace">

          <div className="left-column">

            <UploadPanel

              file={
                file
              }

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

            phase={
              phase
            }

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

            <div className="spinner" />


            <div className="running-content">

              <div className="running-top">

                <strong>
                  Agent 正在处理论文
                </strong>


                {currentNode && (

                  <code>
                    {currentNode}
                  </code>

                )}

              </div>


              <p>
                {progressMessage ||
                  "正在处理..."}
              </p>


              {liveTrace.length > 0 && (

                <div className="live-trace">

                  {liveTrace.map(
                    (node, index) => (

                      <span
                        key={
                          `${node}-${index}`
                        }
                      >

                        {node}

                      </span>

                    )
                  )}

                </div>

              )}

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
          result={
            result
          }
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