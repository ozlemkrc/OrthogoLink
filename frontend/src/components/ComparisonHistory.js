import React, { useEffect, useState } from "react";
import { fetchComparisonHistory } from "../api/client";
import { getSimilarityLevel } from "../utils/similarity";

function ComparisonHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchComparisonHistory(30)
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ marginBottom: 0 }}>Comparison History</h2>
        <span className="badge badge-neutral">{history.length} run{history.length !== 1 ? "s" : ""}</span>
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
            {history.map((item) => (
              <tr key={item.id} className={item.overall_similarity >= 0.7 ? "row-overlap" : ""}>
                <td style={{ color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>
                  {item.id}
                </td>
                <td style={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {item.input_preview}
                </td>
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
                <td style={{ fontSize: "0.78rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
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
