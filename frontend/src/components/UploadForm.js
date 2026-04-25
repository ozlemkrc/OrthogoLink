import React, { useState, useRef, useEffect } from "react";
import { compareText, comparePdf, crossUniversityCompare, fetchStoredUniversities, fetchDepartments } from "../api/client";

const SAMPLE_TEXT = `Course Description
This course introduces modern machine learning with emphasis on model building, evaluation, and deployment. Topics include linear models, decision trees, ensemble methods, neural networks, and unsupervised clustering.

Learning Outcomes
1. Build and tune supervised ML models.
2. Implement neural networks with backpropagation.
3. Evaluate models using cross-validation and metrics.

Course Content
Regression, classification, model selection, regularization, decision trees, random forests, gradient boosting, neural networks, k-means clustering, PCA, deployment considerations.`;

function UploadForm({ onResult }) {
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [uniFilter, setUniFilter] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [universities, setUniversities] = useState([]);
  const [departments, setDepartments] = useState([]);

  // AI explanation options
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiLanguage, setAiLanguage] = useState("tr");

  const fileRef = useRef();

  useEffect(() => {
    fetchStoredUniversities().then((d) => setUniversities(d.universities || [])).catch(() => {});
    fetchDepartments().then((d) => setDepartments(d.departments || [])).catch(() => {});
  }, []);

  const hasFilters = uniFilter || deptFilter;

  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    onResult(null);

    try {
      const aiOptions = { includeAiExplanations: aiEnabled, explanationLanguage: aiLanguage };
      let result;
      if (mode === "text") {
        if (text.trim().length < 50) {
          setError("Please enter at least 50 characters of syllabus text.");
          setLoading(false);
          return;
        }
        if (hasFilters) {
          result = await crossUniversityCompare(
            text,
            uniFilter  ? [uniFilter]  : null,
            deptFilter ? [deptFilter] : null,
            aiOptions,
          );
        } else {
          result = await compareText(text, aiOptions);
        }
      } else {
        if (!file) {
          setError("Please select a PDF file.");
          setLoading(false);
          return;
        }
        result = await comparePdf(file, aiOptions);
      }
      onResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.name.toLowerCase().endsWith(".pdf")) setFile(dropped);
  };

  const clearFilters = () => { setUniFilter(""); setDeptFilter(""); };

  const charCount = text.length;
  const charOk = charCount >= 50;

  return (
    <div className="card">
      <h2>Compare Syllabus</h2>

      {/* Mode toggle */}
      <div className="seg-control">
        <button className={`seg-btn ${mode === "text" ? "active" : ""}`} onClick={() => setMode("text")}>
          ✎ Paste Text
        </button>
        <button className={`seg-btn ${mode === "pdf" ? "active" : ""}`} onClick={() => setMode("pdf")}>
          📄 Upload PDF
        </button>
      </div>

      {/* Text input */}
      {mode === "text" && (
        <>
          <textarea
            placeholder="Paste the full ECTS course form or syllabus text here (course description, learning outcomes, weekly topics, etc.)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ minHeight: 220 }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
            <button className="btn-sm btn-ghost" type="button" onClick={() => setText(SAMPLE_TEXT)}>
              Use Sample Syllabus
            </button>
            <span className={`char-counter ${charCount === 0 ? "" : charOk ? "ok" : "warn"}`}>
              {charCount} chars{charCount > 0 && !charOk ? ` — need ${50 - charCount} more` : ""}
            </span>
          </div>
        </>
      )}

      {/* PDF upload */}
      {mode === "pdf" && (
        <label
          className={`file-upload ${dragOver ? "drag-over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleFileDrop}
          style={{ cursor: "pointer", display: "block" }}
        >
          <span className="file-upload-icon">📄</span>
          <p>{dragOver ? "Drop to upload!" : "Click or drag & drop a PDF here"}</p>
          <p className="hint">Supports ECTS forms and syllabus PDFs</p>
          <input ref={fileRef} type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
          {file && <div className="file-name">✓ {file.name}</div>}
        </label>
      )}

      {/* Filter section — text mode only */}
      {mode === "text" && <div style={{ marginTop: 14 }}>
        <button
          type="button"
          className="btn-sm btn-ghost"
          onClick={() => setShowFilters((v) => !v)}
          style={{ gap: 6 }}
        >
          {showFilters ? "▲" : "▼"} Filter by University / Department
          {hasFilters && (
            <span style={{
              background: "var(--primary)",
              color: "#fff",
              borderRadius: 999,
              fontSize: "0.7rem",
              padding: "1px 6px",
              marginLeft: 4,
            }}>
              {[uniFilter, deptFilter].filter(Boolean).length}
            </span>
          )}
        </button>

        {showFilters && (
          <div style={{
            marginTop: 10,
            padding: "14px 16px",
            background: "var(--surface-alt)",
            borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            alignItems: "flex-end",
          }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label className="add-course-label">University</label>
              <select
                className="input"
                value={uniFilter}
                onChange={(e) => setUniFilter(e.target.value)}
              >
                <option value="">All Universities</option>
                {universities.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>

            <div style={{ flex: 1, minWidth: 200 }}>
              <label className="add-course-label">Department</label>
              <select
                className="input"
                value={deptFilter}
                onChange={(e) => setDeptFilter(e.target.value)}
              >
                <option value="">All Departments</option>
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            {hasFilters && (
              <button type="button" className="btn-sm btn-ghost" onClick={clearFilters} style={{ marginBottom: 1 }}>
                ✕ Clear
              </button>
            )}

          </div>
        )}
      </div>}

      {/* AI explanation controls */}
      <div style={{
        marginTop: 14,
        padding: "12px 16px",
        background: "var(--surface-alt)",
        borderRadius: "var(--radius)",
        border: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        gap: 16,
        flexWrap: "wrap",
      }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontWeight: 500, fontSize: "0.88rem" }}>
          <input
            type="checkbox"
            checked={aiEnabled}
            onChange={(e) => setAiEnabled(e.target.checked)}
            style={{ width: 15, height: 15, cursor: "pointer" }}
          />
          Generate AI explanation for details
        </label>
        {aiEnabled && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label className="add-course-label" style={{ margin: 0, whiteSpace: "nowrap" }}>Language:</label>
            <select
              className="input"
              value={aiLanguage}
              onChange={(e) => setAiLanguage(e.target.value)}
              style={{ padding: "3px 8px", fontSize: "0.85rem", minWidth: 80 }}
            >
              <option value="tr">TR — Türkçe</option>
              <option value="en">EN — English</option>
            </select>
          </div>
        )}
        {aiEnabled && (
          <span style={{ fontSize: "0.76rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
            Requires AI_API_KEY configured on the server
          </span>
        )}
      </div>

      {error && (
        <div className="error-msg" role="alert">
          <span>⚠</span> {error}
        </div>
      )}

      <div className="btn-row">
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={loading || (mode === "text" && charCount === 0) || (mode === "pdf" && !file)}
        >
          {loading ? <><span className="spinner" /> Analyzing…</> : "⊙ Compare Syllabus"}
        </button>
        {(text || file) && !loading && (
          <button
            className="btn-sm btn-ghost"
            onClick={() => { setText(""); setFile(null); setError(""); onResult(null); }}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

export default UploadForm;
