import React, { useEffect, useState } from "react";
import { healthCheck } from "../api/client";

function StatusBar() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await healthCheck();
      setStatus(res);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Health check failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const badgeColor = status?.status === "healthy" ? "badge-unique" : "badge-overlap";

  return (
    <div className="status-bar">
      <div className="status-left">
        <span className={`badge ${badgeColor}`} style={{ marginRight: 8 }}>
          {status?.status || "Unknown"}
        </span>
        {loading && <span className="spinner" style={{ width: 14, height: 14 }} />}
        {!loading && status && (
          <>
            <span>Model: {status.model}</span>
            <span>Threshold: {(status.similarity_threshold * 100).toFixed(0)}%</span>
            <span>Courses: {status.course_count}</span>
            <span>Sections: {status.section_count}</span>
            <span>Index Vectors: {status.index_vectors}</span>
          </>
        )}
        {!loading && error && <span className="error-text">{error}</span>}
      </div>
      <div className="status-actions">
        <button className="btn" style={{ padding: "6px 12px" }} onClick={load}>
          Refresh
        </button>
      </div>
    </div>
  );
}

export default StatusBar;