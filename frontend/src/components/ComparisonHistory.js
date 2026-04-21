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
      <div className="card" style={{ textAlign: "center" }}>
        <span className="spinner" style={{ borderColor: "var(--gray-300)", borderTopColor: "var(--primary)" }} />{" "}
        Loading history...
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="card">
        <h2>Comparison History</h2>
        <div className="empty-state">
          <div className="empty-icon">&#128269;</div>
          <p>No comparisons yet. Run your first comparison from the "Compare Syllabus" tab.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Comparison History ({history.length})</h2>
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
          {history.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
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
              <td style={{ fontSize: "0.8rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ComparisonHistory;
