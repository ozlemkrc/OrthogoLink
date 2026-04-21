import React, { useEffect, useState } from "react";
import { fetchDashboardStats } from "../api/client";
import { getSimilarityLevel } from "../utils/similarity";

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 40 }}>
        <div className="spinner-lg" />
        <p style={{ marginTop: 16, color: "var(--text-secondary)" }}>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return <div className="card error-msg">Failed to load dashboard: {error}</div>;
  }

  if (!stats) return null;

  return (
    <>
      {/* Stats Overview */}
      <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--primary)" }}>{stats.course_count}</div>
          <div className="stat-label">Total Courses</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--primary)" }}>{stats.section_count}</div>
          <div className="stat-label">Course Sections</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--primary)" }}>{stats.index_vectors}</div>
          <div className="stat-label">Index Vectors</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--primary)" }}>{stats.comparison_count}</div>
          <div className="stat-label">Comparisons Run</div>
        </div>
        <div className="stat-card">
          <div className={`stat-value ${getSimilarityLevel(stats.average_similarity)}`}>
            {stats.average_similarity ? `${(stats.average_similarity * 100).toFixed(1)}%` : "N/A"}
          </div>
          <div className="stat-label">Avg Similarity</div>
        </div>
      </div>

      {/* Department Distribution */}
      {stats.department_distribution.length > 0 && (
        <div className="card">
          <h2>Courses by Department</h2>
          <div className="dept-chart">
            {stats.department_distribution.map((dept) => {
              const maxCount = Math.max(...stats.department_distribution.map(d => d.count));
              const pct = (dept.count / maxCount) * 100;
              return (
                <div key={dept.department} className="dept-bar-row">
                  <div className="dept-bar-label">{dept.department}</div>
                  <div className="dept-bar-track">
                    <div
                      className="dept-bar-fill"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="dept-bar-count">{dept.count}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Recent Comparisons */}
      {stats.recent_comparisons.length > 0 && (
        <div className="card">
          <h2>Recent Comparisons</h2>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Input Preview</th>
                <th>Overall Similarity</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_comparisons.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {c.input_preview}
                  </td>
                  <td>
                    <div className="sim-bar-wrap">
                      <span>{(c.overall_similarity * 100).toFixed(1)}%</span>
                      <div className="sim-bar">
                        <div
                          className={`sim-bar-fill ${getSimilarityLevel(c.overall_similarity)}`}
                          style={{ width: `${c.overall_similarity * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Quick Start Guide */}
      {stats.course_count === 0 && (
        <div className="card" style={{ background: "var(--primary-light)", borderColor: "var(--primary)" }}>
          <h2>Getting Started</h2>
          <ol style={{ paddingLeft: 20, lineHeight: 2, color: "var(--text-secondary)" }}>
            <li>Go to <strong>Import from Universities</strong> to import courses from GTU, ITU, METU, Hacettepe, or IYTE</li>
            <li>Or <strong>Add Course</strong> manually by pasting a syllabus</li>
            <li>Use <strong>Compare Syllabus</strong> to check overlap with stored courses</li>
            <li>Use <strong>Cross-University</strong> to compare across multiple universities</li>
          </ol>
        </div>
      )}
    </>
  );
}

export default Dashboard;
