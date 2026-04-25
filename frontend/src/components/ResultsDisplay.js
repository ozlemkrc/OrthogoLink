import React, { useState } from "react";
import { downloadBlob } from "../utils/download";
import { getPercentageLevel, getSimilarityLevel } from "../utils/similarity";

function ResultsDisplay({ data }) {
  const [expandedCourses, setExpandedCourses] = useState({});
  const [expandedSections, setExpandedSections] = useState({});

  if (!data) return null;

  const { overall_similarity, overlap_percentage, top_courses, section_matches, report_summary } = data;

  const downloadReport = () => {
    const blob = new Blob([report_summary], { type: "text/plain" });
    downloadBlob(blob, "orthogonality-report.txt");
  };

  const toggleCourse  = (key) => setExpandedCourses ((prev) => ({ ...prev, [key]: !prev[key] }));
  const toggleSection = (key) => setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));

  const overlapCount = top_courses.filter((c) => c.is_overlap).length;

  return (
    <>
      {/* Header card */}
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ marginBottom: 3 }}>Comparison Results</h2>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.83rem" }}>
            {top_courses.length} course{top_courses.length !== 1 ? "s" : ""} matched
            &nbsp;·&nbsp;
            {overlapCount > 0
              ? <span style={{ color: "var(--danger)", fontWeight: 600 }}>{overlapCount} overlap{overlapCount !== 1 ? "s" : ""} detected</span>
              : <span style={{ color: "var(--success)", fontWeight: 600 }}>No significant overlaps</span>}
            &nbsp;·&nbsp;
            {section_matches.length} section match{section_matches.length !== 1 ? "es" : ""}
          </div>
        </div>
        <button className="btn btn-primary" onClick={downloadReport}>
          ↓ Download Report
        </button>
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

      {/* Top Matching Courses */}
      <div className="card">
        <h2>Top Matching Courses</h2>
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
              </tr>
            </thead>
            <tbody>
              {top_courses.map((course, i) => {
                const key = course.course_code;
                const isOpen = !!expandedCourses[key];
                const detail = course.details;
                return (
                  <React.Fragment key={key}>
                    <tr className={course.is_overlap ? "row-overlap" : ""}>
                      <td style={{ color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>{i + 1}</td>
                      <td>
                        <span style={{
                          fontWeight: 700,
                          color: "var(--primary)",
                          background: "var(--primary-light)",
                          padding: "2px 7px",
                          borderRadius: 5,
                          fontSize: "0.8rem",
                        }}>
                          {course.course_code}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{course.course_name}</td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{course.matched_university || "Unknown"}</div>
                        {course.matched_faculty && (
                          <div style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>
                            {course.matched_faculty}
                          </div>
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
                      <td style={{ minWidth: 240 }}>
                        <div style={{ fontSize: "0.83rem", color: "var(--text-secondary)" }}>
                          {course.explanation || "Semantic content overlap across sections."}
                        </div>
                        {detail && (
                          <button type="button" className="link-btn" onClick={() => toggleCourse(key)}>
                            {isOpen ? "▲ Hide details" : "▼ Show details"}
                          </button>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${course.is_overlap ? "badge-overlap" : "badge-unique"}`}>
                          {course.is_overlap ? "OVERLAP" : "UNIQUE"}
                        </span>
                      </td>
                    </tr>
                    {isOpen && detail && (
                      <tr className="detail-row">
                        <td colSpan={7}>
                          <CourseDetailPanel detail={detail} />
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

      {/* Section-Level Matches */}
      {section_matches.length > 0 && (
        <div className="card">
          <h2>Section-Level Similarity</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Input Section</th>
                  <th>Matched Course</th>
                  <th>Source</th>
                  <th>Matched Section</th>
                  <th>Similarity</th>
                  <th>Why Similar?</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {section_matches.map((match, i) => {
                  const isOpen = !!expandedSections[i];
                  const detail = match.details;
                  return (
                    <React.Fragment key={i}>
                      <tr className={match.is_overlap ? "row-overlap" : ""}>
                        <td style={{ fontWeight: 600, fontSize: "0.83rem" }}>{match.input_section}</td>
                        <td>
                          <span style={{ fontWeight: 700, color: "var(--primary)" }}>{match.matched_course_code}</span>{" "}
                          <span style={{ color: "var(--text-secondary)", fontSize: "0.83rem" }}>{match.matched_course_name}</span>
                        </td>
                        <td>
                          <div>{match.matched_university || "Unknown"}</div>
                          {match.matched_faculty && (
                            <div style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>
                              {match.matched_faculty}
                            </div>
                          )}
                        </td>
                        <td style={{ fontSize: "0.83rem" }}>{match.matched_section}</td>
                        <td>
                          <div className="sim-bar-wrap">
                            <span className={getSimilarityLevel(match.similarity)}>
                              {(match.similarity * 100).toFixed(1)}%
                            </span>
                            <div className="sim-bar">
                              <div
                                className={`sim-bar-fill ${getSimilarityLevel(match.similarity)}`}
                                style={{ width: `${match.similarity * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td style={{ minWidth: 240, fontSize: "0.83rem", color: "var(--text-secondary)" }}>
                          {match.similarity_reason || "Semantic overlap in topic and section intent."}
                          {detail && (
                            <button type="button" className="link-btn" onClick={() => toggleSection(i)}>
                              {isOpen ? "▲ Hide" : "▼ Show details"}
                            </button>
                          )}
                        </td>
                        <td>
                          <span className={`badge ${match.is_overlap ? "badge-overlap" : "badge-unique"}`}>
                            {match.is_overlap ? "OVERLAP" : "OK"}
                          </span>
                        </td>
                      </tr>
                      {isOpen && detail && (
                        <tr className="detail-row">
                          <td colSpan={7}>
                            <SectionDetailPanel match={match} detail={detail} />
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
      )}

      {/* Text Report */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ marginBottom: 0 }}>Analysis Report</h2>
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

function SectionDetailPanel({ match, detail }) {
  return (
    <div className="detail-panel">
      <div className="detail-meta">
        <span>Threshold: <strong>{(detail.threshold * 100).toFixed(0)}%</strong></span>
        <span>This match: <strong>{(match.similarity * 100).toFixed(1)}%</strong></span>
        {detail.shared_keywords?.length > 0 ? (
          <span className="keyword-row">
            Shared terms:
            {detail.shared_keywords.map((kw) => (
              <span key={kw} className="keyword-chip">{kw}</span>
            ))}
          </span>
        ) : (
          <span style={{ color: "var(--gray-500)", fontStyle: "italic" }}>No shared keywords detected.</span>
        )}
      </div>
      <div className="snippet-grid">
        <div className="snippet-card">
          <div className="snippet-title">Your input — {match.input_section}</div>
          <div className="snippet-body">{detail.input_snippet || <em>(no content captured)</em>}</div>
        </div>
        <div className="snippet-card">
          <div className="snippet-title">{match.matched_course_code} — {match.matched_section}</div>
          <div className="snippet-body">{detail.matched_snippet || <em>(no content captured)</em>}</div>
        </div>
      </div>
    </div>
  );
}

function CourseDetailPanel({ detail }) {
  const sourceLabel = {
    ai: "AI",
    ai_cached: "AI (cached)",
    fallback: "Auto-generated",
  }[detail.explanation_source] || null;

  return (
    <div className="detail-panel">
      {detail.ai_explanation && (
        <div className="ai-explanation-block">
          <div className="ai-explanation-header">
            <span className="ai-explanation-label">AI explanation (based on matched evidence)</span>
            {sourceLabel && (
              <span className={`ai-source-badge ${detail.explanation_source === "fallback" ? "ai-source-fallback" : "ai-source-ai"}`}>
                {sourceLabel}
              </span>
            )}
          </div>
          <AiExplanationText text={detail.ai_explanation} />
        </div>
      )}
      <div className="detail-meta">
        <span>Best section similarity: <strong>{(detail.best_similarity * 100).toFixed(1)}%</strong></span>
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
      {detail.contributing_matches?.length > 0 && (
        <div>
          <div className="snippet-title" style={{ marginBottom: 8 }}>Top contributing section pairs</div>
          <ul className="contrib-list">
            {detail.contributing_matches.map((c, idx) => (
              <li key={idx}>
                <span className="contrib-pair">
                  <strong>{c.input_section}</strong> ↔ <strong>{c.matched_section}</strong>
                </span>
                <span className="contrib-score">{(c.similarity * 100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default ResultsDisplay;
