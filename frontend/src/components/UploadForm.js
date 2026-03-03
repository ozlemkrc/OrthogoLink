import React, { useState, useRef } from "react";
import { compareText, comparePdf } from "../api/client";

function UploadForm({ onResult }) {
  const [mode, setMode] = useState("text"); // "text" or "pdf"
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef();

  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    onResult(null);

    try {
      let result;
      if (mode === "text") {
        if (text.trim().length < 50) {
          setError("Please enter at least 50 characters of syllabus text.");
          setLoading(false);
          return;
        }
        result = await compareText(text);
      } else {
        if (!file) {
          setError("Please select a PDF file.");
          setLoading(false);
          return;
        }
        result = await comparePdf(file);
      }
      onResult(result);
    } catch (err) {
      const msg =
        err.response?.data?.detail || err.message || "An error occurred";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.toLowerCase().endsWith(".pdf")) {
      setFile(droppedFile);
    }
  };

  return (
    <div className="card">
      <h2>Upload New Syllabus</h2>

      {/* Mode toggle */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          className={`btn ${mode === "text" ? "btn-primary" : ""}`}
          style={
            mode !== "text"
              ? { background: "var(--gray-100)", color: "var(--gray-700)" }
              : {}
          }
          onClick={() => setMode("text")}
        >
          Paste Text
        </button>
        <button
          className={`btn ${mode === "pdf" ? "btn-primary" : ""}`}
          style={
            mode !== "pdf"
              ? { background: "var(--gray-100)", color: "var(--gray-700)" }
              : {}
          }
          onClick={() => setMode("pdf")}
        >
          Upload PDF
        </button>
      </div>

      {/* Text input */}
      {mode === "text" && (
        <textarea
          placeholder="Paste the full ECTS course form or syllabus text here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      )}

      {/* PDF upload */}
      {mode === "pdf" && (
        <div
          className="file-upload"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
        >
          <div className="icon">📄</div>
          <p>Click or drag & drop a PDF file here</p>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0])}
          />
          {file && <div className="file-name">{file.name}</div>}
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      <div className="btn-row">
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading && <span className="spinner" />}
          {loading ? "Analyzing..." : "Compare Syllabus"}
        </button>
      </div>
    </div>
  );
}

export default UploadForm;
