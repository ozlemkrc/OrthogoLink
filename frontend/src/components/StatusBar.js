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
      setError(err.response?.data?.detail || err.message || "Backend unreachable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const isHealthy = status?.status === "healthy";

  return (
    <div className="status-bar">
      <div className="status-left">
        {loading ? (
          <span className="status-pill">
            <span className="spinner" style={{ width: 12, height: 12, borderTopColor: "var(--primary)" }} />
            Connecting…
          </span>
        ) : error ? (
          <span className="status-pill">
            <span className="status-dot error" />
            Offline — {error}
          </span>
        ) : status ? (
          <>
            <span className="status-pill">
              <span className={`status-dot ${isHealthy ? "healthy" : "error"}`} />
              {isHealthy ? "Healthy" : status.status}
            </span>
            <span className="status-pill">
              <span>🤖</span>
              <strong>{status.model}</strong>
            </span>
            <span className="status-pill">
              Threshold <strong>{(status.similarity_threshold * 100).toFixed(0)}%</strong>
            </span>
            <span className="status-pill">
              <strong>{status.course_count}</strong> courses
            </span>
            <span className="status-pill">
              <strong>{status.section_count}</strong> sections
            </span>
            <span className="status-pill">
              <strong>{status.index_vectors}</strong> vectors
            </span>
          </>
        ) : null}
      </div>

      <div className="status-actions">
        <button
          className="btn-sm btn-ghost"
          onClick={load}
          disabled={loading}
          title="Refresh backend status"
        >
          {loading ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "↻"} Refresh
        </button>
      </div>
    </div>
  );
}

export default StatusBar;
