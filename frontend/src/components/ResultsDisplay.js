import React, { useState } from "react";
import { downloadBlob } from "../utils/download";
import { getPercentageLevel, getSimilarityLevel } from "../utils/similarity";

function ResultsDisplay({ data }) {
  const [expandedCourses, setExpandedCourses] = useState({});
  const [expandedSections, setExpandedSections] = useState({});

  if (!data) return null;

  const {
    overall_similarity,
    overlap_percentage,
    top_courses,
    section_matches,
    report_summary,
  } = data;

  const downloadReport = () => {
    const blob = new Blob([report_summary], { type: "text/plain" });
    downloadBlob(blob, "orthogonality-report.txt");
  };

  const toggleCourse = (key) =>
    setExpandedCourses((prev) => ({ ...prev, [key]: !prev[key] }));

  const toggleSection = (key) =>
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <>
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Comparison Results</h2>
          <div style={{ color: "var(--gray-500)", fontSize: "0.9rem" }}>
            {top_courses.length} course{top_courses.length !== 1 ? "s" : ""} compared &middot; {section_matches.length} section match{section_matches.length !== 1 ? "es" : ""}
          </div>
        </div>
        <button className="btn btn-primary" onClick={downloadReport}>
          Download Report
        </button>
      </div>

      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className={`stat-value ${getSimilarityLevel(overall_similarity)}`}>
            {(overall_similarity * 100).toFixed(1)}%
          </div>
          <div className="stat-label">Overall Similarity</div>
        </div>
        <div className="stat-card">
          <div className={`stat-value ${getPercentageLevel(overlap_percentage)}`}>
            {overlap_percentage.toFixed(1)}%
          </div>
          <div className="stat-label">Overlap Percentage</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--primary)" }}>
            {top_courses.length}
          </div>
          <div className="stat-label">Courses Matched</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--primary)" }}>
            {section_matches.length}
          </div>
          <div className="stat-label">Section Matches</div>
        </div>
      </div>

      {/* Top Matching Courses */}
      <div className="card">
        <h2>Top Matching Courses</h2>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Code</th>
                <th>Course Name</th>
                <th>Source</th>
                <th>Avg Similarity</th>
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
                    <tr>
                      <td>{i + 1}</td>
                      <td>
                        <strong>{course.course_code}</strong>
                      </td>
                      <td>{course.course_name}</td>
                      <td>
                        <div>
                          <div>{course.matched_university || "Unknown source"}</div>
                          {course.matched_faculty ? (
                            <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>
                              {course.matched_faculty}
                            </div>
                          ) : null}
                        </div>
                      </td>
                      <td>
                        <div className="sim-bar-wrap">
                          <span>{(course.average_similarity * 100).toFixed(1)}%</span>
                          <div className="sim-bar">
                            <div
                              className={`sim-bar-fill ${getSimilarityLevel(course.average_similarity)}`}
                              style={{
                                width: `${course.average_similarity * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td style={{ minWidth: 260 }}>
                        <div>{course.explanation || "Semantic content overlap across sections."}</div>
                        {detail ? (
                          <button
                            type="button"
                            className="link-btn"
                            onClick={() => toggleCourse(key)}
                          >
                            {isOpen ? "Hide details" : "Show more details"}
                          </button>
                        ) : null}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            course.is_overlap ? "badge-overlap" : "badge-unique"
                          }`}
                        >
                          {course.is_overlap ? "OVERLAP" : "UNIQUE"}
                        </span>
                      </td>
                    </tr>
                    {isOpen && detail ? (
                      <tr className="detail-row">
                        <td colSpan={7}>
                          <CourseDetailPanel detail={detail} />
                        </td>
                      </tr>
                    ) : null}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section-Level Matches */}
      <div className="card">
        <h2>Section-Level Similarity</h2>
        <div style={{ overflowX: "auto" }}>
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
                    <tr>
                      <td>{match.input_section}</td>
                      <td>
                        <strong>{match.matched_course_code}</strong>{" "}
                        <span style={{ color: "var(--gray-500)" }}>
                          {match.matched_course_name}
                        </span>
                      </td>
                      <td>
                        <div>
                          <div>{match.matched_university || "Unknown source"}</div>
                          {match.matched_faculty ? (
                            <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>
                              {match.matched_faculty}
                            </div>
                          ) : null}
                        </div>
                      </td>
                      <td>{match.matched_section}</td>
                      <td>
                        <div className="sim-bar-wrap">
                          <span>{(match.similarity * 100).toFixed(1)}%</span>
                          <div className="sim-bar">
                            <div
                              className={`sim-bar-fill ${getSimilarityLevel(match.similarity)}`}
                              style={{ width: `${match.similarity * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td style={{ minWidth: 280 }}>
                        <div>{match.similarity_reason || "Semantic overlap in topic and section intent."}</div>
                        {detail ? (
                          <button
                            type="button"
                            className="link-btn"
                            onClick={() => toggleSection(i)}
                          >
                            {isOpen ? "Hide details" : "Show more details"}
                          </button>
                        ) : null}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            match.is_overlap ? "badge-overlap" : "badge-unique"
                          }`}
                        >
                          {match.is_overlap ? "OVERLAP" : "OK"}
                        </span>
                      </td>
                    </tr>
                    {isOpen && detail ? (
                      <tr className="detail-row">
                        <td colSpan={7}>
                          <SectionDetailPanel match={match} detail={detail} />
                        </td>
                      </tr>
                    ) : null}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Text Report */}
      <div className="card">
        <h2>Analysis Report</h2>
        <div className="report">{report_summary}</div>
      </div>
    </>
  );
}

function SectionDetailPanel({ match, detail }) {
  return (
    <div className="detail-panel">
      <div className="detail-meta">
        <span>
          Threshold: <strong>{(detail.threshold * 100).toFixed(0)}%</strong>
        </span>
        <span>
          This match: <strong>{(match.similarity * 100).toFixed(1)}%</strong>
        </span>
        {detail.shared_keywords && detail.shared_keywords.length > 0 ? (
          <span className="keyword-row">
            Shared terms:
            {detail.shared_keywords.map((kw) => (
              <span key={kw} className="keyword-chip">{kw}</span>
            ))}
          </span>
        ) : (
          <span style={{ color: "var(--gray-500)" }}>No shared keywords detected.</span>
        )}
      </div>

      <div className="snippet-grid">
        <div className="snippet-card">
          <div className="snippet-title">Your input — {match.input_section}</div>
          <div className="snippet-body">
            {detail.input_snippet || <em>(no content captured)</em>}
          </div>
        </div>
        <div className="snippet-card">
          <div className="snippet-title">
            {match.matched_course_code} — {match.matched_section}
          </div>
          <div className="snippet-body">
            {detail.matched_snippet || <em>(no content captured)</em>}
          </div>
        </div>
      </div>
    </div>
  );
}

function CourseDetailPanel({ detail }) {
  return (
    <div className="detail-panel">
      <div className="detail-meta">
        <span>
          Best section similarity:{" "}
          <strong>{(detail.best_similarity * 100).toFixed(1)}%</strong>
        </span>
        <span>
          Contributing matches: <strong>{detail.match_count}</strong>
        </span>
        <span>
          Threshold: <strong>{(detail.threshold * 100).toFixed(0)}%</strong>
        </span>
        {detail.shared_keywords && detail.shared_keywords.length > 0 ? (
          <span className="keyword-row">
            Shared terms:
            {detail.shared_keywords.map((kw) => (
              <span key={kw} className="keyword-chip">{kw}</span>
            ))}
          </span>
        ) : null}
      </div>

      {detail.contributing_matches && detail.contributing_matches.length > 0 ? (
        <div>
          <div className="snippet-title" style={{ marginBottom: 6 }}>
            Top contributing section pairs
          </div>
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
      ) : null}
    </div>
  );
}

export default ResultsDisplay;
