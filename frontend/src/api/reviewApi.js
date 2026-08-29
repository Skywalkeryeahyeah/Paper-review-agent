const API_BASE_URL =
  "/api";


async function parseResponse(
  response
) {

  let data;

  try {

    data =
      await response.json();

  } catch {

    throw new Error(
      "后端返回的数据格式不正确"
    );
  }


  if (!response.ok) {

    throw new Error(
      data?.detail ||
      data?.message ||
      `请求失败，状态码：${response.status}`
    );
  }


  return data;
}


export async function uploadPaper(
  file
) {

  const formData =
    new FormData();


  formData.append(
    "file",
    file
  );


  const response =
    await fetch(
      `${API_BASE_URL}/upload`,
      {
        method: "POST",
        body: formData
      }
    );


  return parseResponse(
    response
  );
}


export async function reviewPaper(
  paperId
) {

  const response =
    await fetch(
      `${API_BASE_URL}/papers/${paperId}/review`,
      {
        method: "POST"
      }
    );


  return parseResponse(
    response
  );
}


export function createReviewStream(
  paperId,
  handlers = {}
) {

  const {
    onProgress,
    onResult,
    onAgentError,
    onConnectionError
  } = handlers;


  const url =
    `${API_BASE_URL}/papers/${paperId}/review/stream`;


  const source =
    new EventSource(
      url
    );


  let finished =
    false;


  source.addEventListener(
    "progress",
    (event) => {

      try {

        const data =
          JSON.parse(
            event.data
          );

        onProgress?.(
          data
        );

      } catch (error) {

        console.error(
          "Progress event parse error:",
          error
        );
      }
    }
  );


  source.addEventListener(
    "result",
    (event) => {

      if (finished) {
        return;
      }

      finished = true;


      try {

        const data =
          JSON.parse(
            event.data
          );

        onResult?.(
          data
        );

      } catch (error) {

        onAgentError?.(
          "最终结果解析失败"
        );
      }


      source.close();
    }
  );


  source.addEventListener(
    "agent_error",
    (event) => {

      if (finished) {
        return;
      }

      finished = true;


      let message =
        "Agent 执行失败";


      try {

        const data =
          JSON.parse(
            event.data
          );

        message =
          data.message ||
          message;

      } catch {
        // ignore
      }


      onAgentError?.(
        message
      );


      source.close();
    }
  );


  source.onerror = () => {

    if (finished) {
      return;
    }

    finished = true;


    source.close();


    onConnectionError?.(
      "与 Agent 的实时连接中断"
    );
  };


  return source;
}