import React, { useState, useEffect } from "react";
import { crossUniversityCompare, fetchUniversities, exportCsv } from "../api/client";
import ResultsDisplay from "./ResultsDisplay";
import { downloadBlob } from "../utils/download";

function CrossUniCompare() {
  const [text, setText] = useState("");
  const [universities, setUniversities] = useState([]);
  const [selectedUnis, setSelectedUnis] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchUniversities().then(setUniversities).catch(() => {});
  }, []);

  // Map university codes to course code prefixes
  const uniPrefixMap = {
    gtu: ["BLM", "ELK", "MAK", "END", "KIM", "MAT", "FIZ"],
    itu: ["BLG", "YZV", "EHB", "KON"],
    metu: ["CENG", "EEE", "IE", "MATH", "STAT"],
    hacettepe: ["BBM", "EEM", "IST"],
    iyte: ["CENG", "EEE", "ME"],
  };

  const handleUniToggle = (code) => {
    setSelectedUnis((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleCompare = async () => {
    setError("");
    setLoading(true);
    setResults(null);

    try {
      if (text.trim().length < 50) {
        setError("Please enter at least 50 characters of syllabus text.");
        setLoading(false);
        return;
      }

      // Collect all course code prefixes for selected universities
      let universityFilter = null;
      if (selectedUnis.length > 0) {
        universityFilter = selectedUnis.flatMap((code) => uniPrefixMap[code] || []);
      }

      const result = await crossUniversityCompare(text, universityFilter);
      setResults(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = async () => {
    try {
      const blob = await exportCsv(text);
      downloadBlob(blob, "orthogonality-report.csv");
    } catch (err) {
      setError("CSV export failed");
    }
  };

  const SAMPLE_TEXT = `Course Description
This course introduces modern artificial intelligence concepts including search algorithms, knowledge representation, machine learning fundamentals, and neural network architectures.

Learning Outcomes
1. Understand AI problem formulation and search strategies
2. Apply machine learning algorithms to real-world datasets
3. Design and train neural networks
4. Evaluate model performance with appropriate metrics

Course Content
Introduction to AI, intelligent agents, uninformed and informed search, adversarial search, constraint satisfaction, knowledge representation, probabilistic reasoning, supervised learning (regression, classification), unsupervised learning (clustering, dimensionality reduction), neural networks, deep learning introduction, natural language processing overview.

Assessment
Midterm: 30%, Final: 35%, Projects: 35%`;

  return (
    <>
      <div className="card">
        <h2>Cross-University Comparison</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
          Compare a syllabus against courses from specific universities. Select which universities
          to include in the comparison, or leave all unselected to compare against all stored courses.
        </p>

        {/* University Selection */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontWeight: 600, display: "block", marginBottom: 8 }}>
            Filter by University (optional)
          </label>
          <div className="uni-filter-grid">
            {universities.map((uni) => (
              <label
                key={uni.code}
                className={`checkbox-card ${selectedUnis.includes(uni.code) ? "selected" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={selectedUnis.includes(uni.code)}
                  onChange={() => handleUniToggle(uni.code)}
                />
                <div>
                  <strong>{uni.code.toUpperCase()}</strong>
                  <span>{uni.name}</span>
                </div>
              </label>
            ))}
          </div>
          {selectedUnis.length > 0 && (
            <div style={{ marginTop: 8, fontSize: "0.85rem", color: "var(--primary)" }}>
              Comparing against: {selectedUnis.map(c => c.toUpperCase()).join(", ")}
            </div>
          )}
        </div>

        {/* Text Input */}
        <textarea
          placeholder="Paste the full ECTS course form or syllabus text here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ minHeight: 200 }}
        />

        <div className="btn-row" style={{ marginTop: 8 }}>
          <button
            className="btn"
            onClick={() => setText(SAMPLE_TEXT)}
            style={{ background: "var(--gray-100)", color: "var(--gray-700)" }}
          >
            Use Sample
          </button>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="btn-row">
          <button className="btn btn-primary" onClick={handleCompare} disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Analyzing..." : "Compare Across Universities"}
          </button>
          {results && (
            <button className="btn btn-secondary" onClick={handleExportCsv}>
              Export CSV
            </button>
          )}
        </div>
      </div>

      {results && <ResultsDisplay data={results} />}
    </>
  );
}

export default CrossUniCompare;
