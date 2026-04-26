import React, { useEffect, useState } from "react";
import { fetchComparisonHistory } from "../api/client";
import { getSimilarityLevel } from "../utils/similarity";

function ComparisonHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [search, setSearch] = useState("");
  const [onlyOverlaps, setOnlyOverlaps] = useState(false);

  useEffect(() => {
    fetchComparisonHistory(30)
      .then(setHistory)
      .catch((err) => {
        if (err.response?.status === 401) setAuthRequired(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const visible = history.filter((item) => {
    if (onlyOverlaps && item.overall_similarity < 0.7) return false;
    if (search && !(item.input_preview || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="card">
        <div className="loading-state">
          <div className="spinner-lg" />
          <p>Loading history…</p>
        </div>
      </div>
    );
  }

  if (authRequired) {
    return (
      <div className="card">
        <h2>Comparison History</h2>
        <div className="empty-state">
          <span className="empty-icon">🔒</span>
          <h3>Login required</h3>
          <p>Please log in to view comparison history.</p>
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="card">
        <h2>Comparison History</h2>
        <div className="empty-state">
          <span className="empty-icon">🔍</span>
          <h3>No comparisons yet</h3>
          <p>Run your first comparison from the <strong>Compare Syllabus</strong> tab to see results here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-row">
        <h2>Comparison History</h2>
        <span className="badge badge-neutral">{history.length} run{history.length !== 1 ? "s" : ""}</span>
      </div>

      <div className="table-toolbar">
        <input
          className="search-input"
          type="search"
          placeholder="Search input preview…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label className={`toggle-pill ${onlyOverlaps ? "active" : ""}`}>
          <input
            type="checkbox"
            checked={onlyOverlaps}
            onChange={(e) => setOnlyOverlaps(e.target.checked)}
          />
          High-similarity only
        </label>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 50 }}>#</th>
              <th>Input Preview</th>
              <th style={{ width: 160 }}>Overall Similarity</th>
              <th style={{ width: 140 }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr className="empty-row">
                <td colSpan={4}>No matching runs.</td>
              </tr>
            )}
            {visible.map((item) => (
              <tr key={item.id} className={item.overall_similarity >= 0.7 ? "row-overlap" : ""}>
                <td className="cell-id">{item.id}</td>
                <td className="cell-preview">{item.input_preview}</td>
                <td>
                  <div className="sim-bar-wrap">
                    <span className={getSimilarityLevel(item.overall_similarity)}>
                      {(item.overall_similarity * 100).toFixed(1)}%
                    </span>
                    <div className="sim-bar">
                      <div
                        className={`sim-bar-fill ${getSimilarityLevel(item.overall_similarity)}`}
                        style={{ width: `${item.overall_similarity * 100}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td className="cell-meta">
                  {item.created_at
                    ? new Date(item.created_at).toLocaleString(undefined, {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                      })
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ComparisonHistory;
