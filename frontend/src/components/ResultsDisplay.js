import React, { useEffect, useState } from "react";
import { downloadBlob } from "../utils/download";
import { getPercentageLevel, getSimilarityLevel } from "../utils/similarity";
import { fetchCourse } from "../api/client";

function ResultsDisplay({ data }) {
  const [expandedCourse, setExpandedCourse] = useState(null);
  const [onlyOverlaps, setOnlyOverlaps] = useState(false);

  if (!data) return null;

  const { overall_similarity, overlap_percentage, top_courses, section_matches, report_summary, ai_summary, ai_summary_source } = data;

  const downloadReport = () => {
    const blob = new Blob([report_summary], { type: "text/plain" });
    downloadBlob(blob, "orthogonality-report.txt");
  };

  const overlapCount = top_courses.filter((c) => c.is_overlap).length;
  const sectionOverlapCount = section_matches.filter((m) => m.is_overlap).length;

  let verdictTone = "unique";
  let verdictIcon = "✓";
  let verdictTitle = "Course is sufficiently unique";
  let verdictText = `No significant overlaps found across ${top_courses.length} matched course${top_courses.length !== 1 ? "s" : ""}. The proposed syllabus appears orthogonal to the existing catalog.`;

  if (overlapCount > 0) {
    verdictTone = overlapCount >= 3 ? "overlap" : "moderate";
    verdictIcon = overlapCount >= 3 ? "✕" : "!";
    verdictTitle = `${overlapCount} overlapping course${overlapCount !== 1 ? "s" : ""} detected`;
    verdictText = `${overlapCount} of ${top_courses.length} matched courses cross the overlap threshold` +
      (sectionOverlapCount > 0 ? `, with ${sectionOverlapCount} section-level conflict${sectionOverlapCount !== 1 ? "s" : ""}.` : ".") +
      " Expand a row to see its full syllabus and section-level breakdown.";
  }

  const visibleCourses = onlyOverlaps ? top_courses.filter((c) => c.is_overlap) : top_courses;

  const sectionMatchesByCourse = section_matches.reduce((acc, m) => {
    (acc[m.matched_course_code] = acc[m.matched_course_code] || []).push(m);
    return acc;
  }, {});

  const toggleExpand = (code) => {
    setExpandedCourse((prev) => (prev === code ? null : code));
  };

  return (
    <>
      {/* Verdict banner */}
      <div className={`verdict ${verdictTone}`}>
        <div className="verdict-icon">{verdictIcon}</div>
        <div className="verdict-body">
          <div className="verdict-title">{verdictTitle}</div>
          <div className="verdict-text">{verdictText}</div>
        </div>
        <div className="verdict-actions">
          <button className="btn btn-primary" onClick={downloadReport}>
            ↓ Download Report
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-card-icon">〜</span>
          <div className={`stat-value ${getSimilarityLevel(overall_similarity)}`}>
            {(overall_similarity * 100).toFixed(1)}%
          </div>
          <div className="stat-label">Overall Similarity</div>
        </div>
        <div className="stat-card">
          <span className="stat-card-icon">⊗</span>
          <div className={`stat-value ${getPercentageLevel(overlap_percentage)}`}>
            {overlap_percentage.toFixed(1)}%
          </div>
          <div className="stat-label">Overlap %</div>
        </div>
        <div className="stat-card">
          <span className="stat-card-icon">📚</span>
          <div className="stat-value primary">{top_courses.length}</div>
          <div className="stat-label">Courses Matched</div>
        </div>
        <div className="stat-card">
          <span className="stat-card-icon">📑</span>
          <div className="stat-value primary">{section_matches.length}</div>
          <div className="stat-label">Section Matches</div>
        </div>
      </div>

      {/* AI Summary */}
      {ai_summary && (
        <div className="card ai-summary-card">
          <div className="ai-summary-header">
            <span className="ai-summary-label">AI Analysis</span>
            {ai_summary_source && ai_summary_source !== "fallback" && (
              <span className="ai-source-badge ai-source-ai">AI</span>
            )}
          </div>
          <AiExplanationText text={ai_summary} />
        </div>
      )}

      {/* Top Matching Courses */}
      <div className="card">
        <div className="card-row">
          <div>
            <h2>Top Matching Courses</h2>
            <div className="results-meta">Click the arrow to view a course's full syllabus and section-level breakdown.</div>
          </div>
          <label className={`toggle-pill ${onlyOverlaps ? "active" : ""}`}>
            <input
              type="checkbox"
              checked={onlyOverlaps}
              onChange={(e) => setOnlyOverlaps(e.target.checked)}
            />
            Show only overlaps {overlapCount > 0 && `(${overlapCount})`}
          </label>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: 40 }}>#</th>
                <th>Code</th>
                <th>Course Name</th>
                <th>Source</th>
                <th>Similarity</th>
                <th>Why Similar?</th>
                <th>Status</th>
                <th style={{ width: 56 }} aria-label="Expand"></th>
              </tr>
            </thead>
            <tbody>
              {visibleCourses.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={8}>No overlapping courses to show.</td>
                </tr>
              )}
              {visibleCourses.map((course, i) => {
                const code = course.course_code;
                const isOpen = expandedCourse === code;
                const courseSectionMatches = sectionMatchesByCourse[code] || [];
                return (
                  <React.Fragment key={code}>
                    <tr
                      className={[
                        "row-selectable",
                        course.is_overlap ? "row-overlap" : "",
                        isOpen ? "row-selected" : "",
                      ].filter(Boolean).join(" ")}
                      onClick={() => toggleExpand(code)}
                    >
                      <td className="cell-id">{i + 1}</td>
                      <td>
                        <span className="course-code-pill">{course.course_code}</span>
                      </td>
                      <td style={{ fontWeight: 500 }}>
                        {course.course_name}
                        {courseSectionMatches.length > 0 && (
                          <span className="link-count-chip" title="Section-level matches">
                            {courseSectionMatches.length} section{courseSectionMatches.length !== 1 ? "s" : ""}
                          </span>
                        )}
                      </td>
                      <td className="source-cell">
                        <div className="source-name">{course.matched_university || "Unknown"}</div>
                        {course.matched_faculty && (
                          <div className="source-faculty">{course.matched_faculty}</div>
                        )}
                      </td>
                      <td>
                        <div className="sim-bar-wrap">
                          <span className={getSimilarityLevel(course.average_similarity)}>
                            {(course.average_similarity * 100).toFixed(1)}%
                          </span>
                          <div className="sim-bar">
                            <div
                              className={`sim-bar-fill ${getSimilarityLevel(course.average_similarity)}`}
                              style={{ width: `${course.average_similarity * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="why-cell">
                        <div className="why-text">
                          {course.explanation || "Semantic content overlap across sections."}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${course.is_overlap ? "badge-overlap" : "badge-unique"}`}>
                          {course.is_overlap ? "OVERLAP" : "UNIQUE"}
                        </span>
                      </td>
                      <td className="expand-cell">
                        <span className={`expand-chevron ${isOpen ? "open" : ""}`} aria-label={isOpen ? "Collapse" : "Expand"}>
                          ▶
                        </span>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="detail-row">
                        <td colSpan={8}>
                          <CourseExpandedDetails
                            course={course}
                            sectionMatches={courseSectionMatches}
                          />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Text Report */}
      <div className="card">
        <div className="card-row">
          <h2>Analysis Report</h2>
          <button className="btn-sm btn-ghost" onClick={downloadReport}>↓ Download</button>
        </div>
        <div className="report">{report_summary}</div>
      </div>
    </>
  );
}

function renderInlineMarkdown(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

function AiExplanationText({ text }) {
  if (!text) return null;

  const cleaned = text.replace(/\s+(\d+\.\s\*\*)/g, "\n$1").trim();
  const items = cleaned.split(/\n(?=\d+\.\s)/).map((s) => s.trim()).filter(Boolean);

  const isNumberedList = items.length > 1 && items.every((s) => /^\d+\.\s/.test(s));

  if (!isNumberedList) {
    return <p className="ai-explanation-text">{renderInlineMarkdown(text)}</p>;
  }

  return (
    <ol className="ai-explanation-list">
      {items.map((item, i) => {
        const body = item.replace(/^\d+\.\s/, "");
        return <li key={i}>{renderInlineMarkdown(body)}</li>;
      })}
    </ol>
  );
}

function CourseExpandedDetails({ course, sectionMatches }) {
  const [fullCourse, setFullCourse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!course.course_id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchCourse(course.course_id)
      .then((data) => { if (!cancelled) setFullCourse(data); })
      .catch((err) => { if (!cancelled) setError(err.response?.data?.detail || "Failed to load course."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [course.course_id]);

  const detail = course.details;

  return (
    <div className="course-expanded">
      <div className="course-info-grid">
        <InfoCell label="Code" value={course.course_code} />
        <InfoCell label="University" value={course.matched_university || fullCourse?.university} />
        <InfoCell label="Faculty" value={course.matched_faculty || fullCourse?.faculty} />
        <InfoCell label="Department" value={fullCourse?.department} />
        <InfoCell label="Credits" value={fullCourse?.credits} />
        <InfoCell
          label="Course Similarity"
          value={`${(course.average_similarity * 100).toFixed(1)}%`}
          tone={getSimilarityLevel(course.average_similarity)}
        />
      </div>

      {loading && (
        <div className="loading-state" style={{ padding: "16px 0" }}>
          <div className="spinner" /> <span>Loading full course details…</span>
        </div>
      )}

      {error && <div className="error-msg" role="alert"><span>⚠</span> {error}</div>}

      {fullCourse?.description && (
        <div className="course-info-block">
          <div className="snippet-title">Course Description</div>
          <div className="course-description-text">{fullCourse.description}</div>
        </div>
      )}

      {sectionMatches.length > 0 && (
        <div className="course-info-block">
          <div className="snippet-title">Section-Level Similarity ({sectionMatches.length})</div>
          <div className="inner-table-wrap">
            <table className="inner-table">
              <thead>
                <tr>
                  <th>Your Section</th>
                  <th>Their Section</th>
                  <th>Similarity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sectionMatches.map((m, i) => (
                  <tr key={i} className={m.is_overlap ? "row-overlap" : ""}>
                    <td className="section-cell">{m.input_section}</td>
                    <td className="section-name-cell">{m.matched_section}</td>
                    <td>
                      <div className="sim-bar-wrap">
                        <span className={getSimilarityLevel(m.similarity)}>
                          {(m.similarity * 100).toFixed(1)}%
                        </span>
                        <div className="sim-bar">
                          <div
                            className={`sim-bar-fill ${getSimilarityLevel(m.similarity)}`}
                            style={{ width: `${m.similarity * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${m.is_overlap ? "badge-overlap" : "badge-unique"}`}>
                        {m.is_overlap ? "OVERLAP" : "OK"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {fullCourse?.sections?.length > 0 && (
        <details className="syllabus-details">
          <summary>Full syllabus — {fullCourse.sections.length} section{fullCourse.sections.length !== 1 ? "s" : ""}</summary>
          <div className="syllabus-list">
            {fullCourse.sections.map((sec) => (
              <div key={sec.id} className="syllabus-section">
                <div className="syllabus-section-heading">{sec.heading}</div>
                <div className="syllabus-section-body">{sec.content || <em>(empty)</em>}</div>
              </div>
            ))}
          </div>
        </details>
      )}

      {detail && (
        <div className="detail-meta">
          <span>Best section: <strong>{(detail.best_similarity * 100).toFixed(1)}%</strong></span>
          <span>Contributing matches: <strong>{detail.match_count}</strong></span>
          <span>Threshold: <strong>{(detail.threshold * 100).toFixed(0)}%</strong></span>
          {detail.shared_keywords?.length > 0 && (
            <span className="keyword-row">
              Shared terms:
              {detail.shared_keywords.map((kw) => (
                <span key={kw} className="keyword-chip">{kw}</span>
              ))}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function InfoCell({ label, value, tone }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="info-cell">
      <div className="info-cell-label">{label}</div>
      <div className={`info-cell-value ${tone || ""}`}>{value}</div>
    </div>
  );
}

export default ResultsDisplay;
