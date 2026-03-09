import React from "react";

function ResultsDisplay({ data }) {
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
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "orthogonality-report.txt";
    link.click();
    URL.revokeObjectURL(url);
  };

  const simLevel = (val) => {
    if (val >= 0.7) return "high";
    if (val >= 0.4) return "moderate";
    return "low";
  };

  const pctLevel = (val) => {
    if (val > 50) return "high";
    if (val > 25) return "moderate";
    return "low";
  };

  return (
    <>
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Comparison Results</h2>
          <div style={{ color: "var(--gray-500)", fontSize: "0.9rem" }}>
            Review overlap metrics below. Export the full narrative report as needed.
          </div>
        </div>
        <button className="btn btn-primary" onClick={downloadReport}>
          Download Report (.txt)
        </button>
      </div>

      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className={`stat-value ${simLevel(overall_similarity)}`}>
            {(overall_similarity * 100).toFixed(1)}%
          </div>
          <div className="stat-label">Overall Similarity</div>
        </div>
        <div className="stat-card">
          <div className={`stat-value ${pctLevel(overlap_percentage)}`}>
            {overlap_percentage.toFixed(1)}%
          </div>
          <div className="stat-label">Overlap Percentage</div>
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
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Code</th>
              <th>Course Name</th>
              <th>Avg Similarity</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {top_courses.map((course, i) => (
              <tr key={course.course_code}>
                <td>{i + 1}</td>
                <td>
                  <strong>{course.course_code}</strong>
                </td>
                <td>{course.course_name}</td>
                <td>
                  <div className="sim-bar-wrap">
                    <span>{(course.average_similarity * 100).toFixed(1)}%</span>
                    <div className="sim-bar">
                      <div
                        className={`sim-bar-fill ${simLevel(course.average_similarity)}`}
                        style={{
                          width: `${course.average_similarity * 100}%`,
                        }}
                      />
                    </div>
                  </div>
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
            ))}
          </tbody>
        </table>
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
                <th>Matched Section</th>
                <th>Similarity</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {section_matches.map((match, i) => (
                <tr key={i}>
                  <td>{match.input_section}</td>
                  <td>
                    <strong>{match.matched_course_code}</strong>{" "}
                    <span style={{ color: "var(--gray-500)" }}>
                      {match.matched_course_name}
                    </span>
                  </td>
                  <td>{match.matched_section}</td>
                  <td>
                    <div className="sim-bar-wrap">
                      <span>{(match.similarity * 100).toFixed(1)}%</span>
                      <div className="sim-bar">
                        <div
                          className={`sim-bar-fill ${simLevel(match.similarity)}`}
                          style={{ width: `${match.similarity * 100}%` }}
                        />
                      </div>
                    </div>
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
              ))}
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

export default ResultsDisplay;
