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

function Dashboard({ onNavigate }) {
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
      {/* Primary call-to-action — the comparison flow is the core of the product */}
      <div className="start-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>⊙ Check a new course for overlap</h2>
          <p style={{ margin: 0, color: "var(--text-secondary)" }}>
            Paste an ECTS form or upload a syllabus PDF to see how much it overlaps with the {stats.course_count} stored course{stats.course_count !== 1 ? "s" : ""}.
          </p>
        </div>
        {onNavigate && (
          <button className="btn btn-primary" onClick={() => onNavigate("compare")} style={{ flexShrink: 0 }}>
            Compare a Syllabus →
          </button>
        )}
      </div>

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

      {/* Getting Started Guide */}
      {stats.course_count === 0 && (
        <div className="start-banner">
          <h2>🚀 Getting Started</h2>
          <ol className="start-steps">
            {[
              <>Go to <strong>Import from Universities</strong> to bulk-import courses from GTU, METU, Hacettepe, or IYTE</>,
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

      {/* About / How it works — a short readme to orient new users */}
      <div className="card">
        <h2>ℹ️ About OrthogoLink</h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, marginTop: 4 }}>
          OrthogoLink is an AI-powered <strong>curriculum orthogonality checker</strong>. When a new course is
          proposed, it compares the proposal's syllabus and ECTS content against the existing course catalogue —
          and against other Turkish universities — to measure how much they overlap, where, and by how much.
          The goal is to keep each course distinct and prevent curriculum bloat.
        </p>

        <div className="how-it-works" style={{ marginTop: 18 }}>
          {[
            {
              icon: "⊙",
              title: "1 · Compare a syllabus",
              body: <>Open <strong>Compare Syllabus</strong>, paste the ECTS form text or upload a PDF, pick a similarity threshold, then run the analysis to get an overlap report against the stored catalogue.</>,
            },
            {
              icon: "≡",
              title: "2 · Browse stored courses",
              body: <>The <strong>Stored Courses</strong> tab holds every course in the index. Use search and the university / department filters to narrow what you compare against.</>,
            },
            {
              icon: "⏱",
              title: "3 · Review past runs",
              body: <>Every comparison you run while logged in is saved to <strong>History</strong>, so you can revisit overall similarity scores and inputs later.</>,
            },
            {
              icon: "↓",
              title: "4 · Grow the catalogue (admin)",
              body: <>Admins can <strong>Add Course</strong> manually or <strong>Import from Universities</strong> (GTU, METU, Hacettepe, IYTE) to expand the pool the checker compares against.</>,
            },
          ].map((item) => (
            <div
              key={item.title}
              style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "10px 0", borderTop: "1px solid var(--border)" }}
            >
              <span style={{ fontSize: "1.3rem", color: "var(--primary)", lineHeight: 1.2 }}>{item.icon}</span>
              <div>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>{item.title}</div>
                <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.5 }}>{item.body}</div>
              </div>
            </div>
          ))}
        </div>

        <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem", marginTop: 14 }}>
          💡 Similarity is computed from semantic embeddings of the course text. A higher percentage means the
          proposed course covers topics already taught elsewhere — review those matches before approving it.
        </p>
      </div>
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
