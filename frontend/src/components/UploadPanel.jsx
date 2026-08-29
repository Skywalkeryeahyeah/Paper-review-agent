export default function UploadPanel({
  file,
  onFileChange,
  onStart,
  loading
}) {

  function handleChange(event) {
    const selectedFile = event.target.files?.[0];

    if (selectedFile) {
      onFileChange(selectedFile);
    }
  }

  function handleDrop(event) {
    event.preventDefault();

    const droppedFile =
      event.dataTransfer.files?.[0];

    if (!droppedFile) {
      return;
    }

    if (
      droppedFile.type !== "application/pdf" &&
      !droppedFile.name
        .toLowerCase()
        .endsWith(".pdf")
    ) {
      alert("请选择 PDF 文件");
      return;
    }

    onFileChange(droppedFile);
  }

  function handleDragOver(event) {
    event.preventDefault();
  }

  return (
    <section className="upload-card">

      <div className="section-heading">
        <span className="section-number">
          01
        </span>

        <div>
          <h2>上传论文</h2>

          <p>
            上传需要进行智能审稿的学术论文 PDF
          </p>
        </div>
      </div>

      <label
        className="drop-zone"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >

        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleChange}
          disabled={loading}
        />

        <div className="upload-icon">
          ↑
        </div>

        <strong>
          点击选择 PDF
        </strong>

        <span>
          或将论文拖放到这里
        </span>

      </label>

      {file && (
        <div className="selected-file">

          <div className="file-icon">
            PDF
          </div>

          <div className="file-info">

            <strong>
              {file.name}
            </strong>

            <span>
              {(file.size / 1024 / 1024)
                .toFixed(2)} MB
            </span>

          </div>

        </div>
      )}

      <button
        className="review-button"
        disabled={!file || loading}
        onClick={onStart}
      >
        {loading
          ? "Agent 正在审稿..."
          : "开始智能审稿"}
      </button>

    </section>
  );
}