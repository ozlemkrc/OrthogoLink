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

  // Similarity threshold (percent). 70% is the default cutoff.
  const [threshold, setThreshold] = useState(70);

  // AI explanation options
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiLanguage, setAiLanguage] = useState("en");

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
      const aiOptions = {
        includeAiExplanations: aiEnabled,
        explanationLanguage: aiLanguage,
        customThreshold: threshold / 100,
      };
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
        result = await comparePdf(file, {
          ...aiOptions,
          universityFilter: uniFilter ? [uniFilter] : null,
          departmentFilter: deptFilter ? [deptFilter] : null,
        });
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
          {!text && (
            <div className="sample-hint">
              <span>💡 New here?</span>
              <button type="button" onClick={() => setText(SAMPLE_TEXT)}>
                Try a sample syllabus →
              </button>
            </div>
          )}
          <textarea
            placeholder="Paste the full ECTS course form or syllabus text here (course description, learning outcomes, weekly topics, etc.)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ minHeight: 220 }}
          />
          <div className="upload-toggle-row">
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

      {/* Filter section */}
      <div className="filter-section">
        <button
          type="button"
          className="btn-sm btn-ghost filter-toggle-btn"
          onClick={() => setShowFilters((v) => !v)}
        >
          {showFilters ? "▲" : "▼"} Filter by University / Department
          {hasFilters && (
            <span className="filter-count-badge">
              {[uniFilter, deptFilter].filter(Boolean).length}
            </span>
          )}
        </button>

        {hasFilters && !showFilters && (
          <div className="active-filters">
            <span className="active-filters-label">Active:</span>
            {uniFilter && (
              <span className="filter-chip">
                {uniFilter}
                <button type="button" onClick={() => setUniFilter("")} aria-label="Remove university filter">×</button>
              </span>
            )}
            {deptFilter && (
              <span className="filter-chip">
                {deptFilter}
                <button type="button" onClick={() => setDeptFilter("")} aria-label="Remove department filter">×</button>
              </span>
            )}
          </div>
        )}

        {showFilters && (
          <div className="filter-panel">
            <div className="filter-field">
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

            <div className="filter-field">
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
              <button type="button" className="btn-sm btn-ghost" onClick={clearFilters}>
                ✕ Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Similarity threshold */}
      <div className="threshold-row">
        <span className="add-course-label" title="Matches at or above this similarity are flagged as overlaps">
          Similarity threshold
        </span>
        <div className="threshold-chips">
          {[50, 60, 70, 80, 90].map((v) => (
            <button
              key={v}
              type="button"
              className={`threshold-chip ${threshold === v ? "active" : ""}`}
              onClick={() => setThreshold(v)}
            >
              {v}%
            </button>
          ))}
        </div>
      </div>

      {/* AI explanation controls */}
      <div className="ai-panel">
        <label className="ai-checkbox-label">
          <input
            type="checkbox"
            checked={aiEnabled}
            onChange={(e) => setAiEnabled(e.target.checked)}
          />
          <span className="ai-panel-icon">✨</span>
          Generate AI explanation for details
        </label>
        {aiEnabled && (
          <div className="ai-lang-row">
            <label className="add-course-label">Language:</label>
            <select
              className="input input-sm"
              value={aiLanguage}
              onChange={(e) => setAiLanguage(e.target.value)}
            >
              <option value="tr">TR — Türkçe</option>
              <option value="en">EN — English</option>
            </select>
          </div>
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
