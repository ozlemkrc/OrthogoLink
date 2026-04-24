import React, { useEffect, useState } from "react";
import { fetchDashboardStats } from "../api/client";
import { getSimilarityLevel } from "../utils/similarity";

const STAT_ICONS = {
  courses:     "📚",
  sections:    "📑",
  vectors:     "🔢",
  comparisons: "📊",
  similarity:  "〜",
};

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
      <div className="card">
        <div className="loading-state">
          <div className="spinner-lg" />
          <p>Loading dashboard…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card error-msg">
        <span>⚠</span> Failed to load dashboard: {error}
      </div>
    );
  }

  if (!stats) return null;

  const avgSim = stats.average_similarity
    ? `${(stats.average_similarity * 100).toFixed(1)}%`
    : "N/A";

  return (
    <>
      {/* Stats Overview */}
      <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
        <StatCard icon={STAT_ICONS.courses}     value={stats.course_count}     label="Total Courses"    className="primary" />
        <StatCard icon={STAT_ICONS.sections}    value={stats.section_count}    label="Course Sections"  className="primary" />
        <StatCard icon={STAT_ICONS.vectors}     value={stats.index_vectors}    label="Index Vectors"    className="primary" />
        <StatCard icon={STAT_ICONS.comparisons} value={stats.comparison_count} label="Comparisons Run"  className="primary" />
        <StatCard
          icon={STAT_ICONS.similarity}
          value={avgSim}
          label="Avg Similarity"
          className={stats.average_similarity ? getSimilarityLevel(stats.average_similarity) : "primary"}
        />
      </div>

      {/* Department Distribution */}
      {stats.department_distribution.length > 0 && (
        <div className="card">
          <h2>Courses by Department</h2>
          <div className="dept-chart">
            {stats.department_distribution.map((dept) => {
              const maxCount = Math.max(...stats.department_distribution.map((d) => d.count));
              const pct = (dept.count / maxCount) * 100;
              return (
                <div key={dept.department} className="dept-bar-row">
                  <div className="dept-bar-label" title={dept.department}>{dept.department}</div>
                  <div className="dept-bar-track">
                    <div className="dept-bar-fill" style={{ width: `${pct}%` }} />
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
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Input Preview</th>
                  <th>Similarity</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_comparisons.map((c) => (
                  <tr key={c.id}>
                    <td style={{ color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>{c.id}</td>
                    <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {c.input_preview}
                    </td>
                    <td>
                      <div className="sim-bar-wrap">
                        <span className={getSimilarityLevel(c.overall_similarity)}>
                          {(c.overall_similarity * 100).toFixed(1)}%
                        </span>
                        <div className="sim-bar">
                          <div
                            className={`sim-bar-fill ${getSimilarityLevel(c.overall_similarity)}`}
                            style={{ width: `${c.overall_similarity * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td style={{ fontSize: "0.78rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                      {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Getting Started Guide */}
      {stats.course_count === 0 && (
        <div className="start-banner">
          <h2>🚀 Getting Started</h2>
          <ol className="start-steps">
            {[
              <>Go to <strong>Import from Universities</strong> to bulk-import courses from GTU, ITU, METU, Hacettepe, or IYTE</>,
              <>Or use <strong>Add Course</strong> to manually paste a syllabus</>,
              <>Run <strong>Compare Syllabus</strong> to detect overlap with stored courses</>,
              <>Use <strong>Cross-University</strong> to benchmark across multiple institutions</>,
            ].map((step, i) => (
              <li key={i} className="start-step">
                <span className="start-step-num">{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </>
  );
}

function StatCard({ icon, value, label, className = "primary" }) {
  return (
    <div className="stat-card">
      <span className="stat-card-icon">{icon}</span>
      <div className={`stat-value ${className}`}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default Dashboard;
