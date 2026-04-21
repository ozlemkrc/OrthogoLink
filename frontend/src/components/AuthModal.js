import React, { useState } from "react";
import { login, register } from "../api/client";

function AuthModal({ onLogin, onClose }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let result;
      if (mode === "login") {
        result = await login(username, password);
      } else {
        result = await register(username, password, fullName);
      }
      onLogin(result);
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2>{mode === "login" ? "Login" : "Register"}</h2>
          <button className="btn-sm btn-ghost" onClick={onClose} style={{ fontSize: "1.2rem" }}>
            &times;
          </button>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button
            className={`btn ${mode === "login" ? "btn-primary" : ""}`}
            style={mode !== "login" ? { background: "var(--gray-100)", color: "var(--gray-700)" } : {}}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            className={`btn ${mode === "register" ? "btn-primary" : ""}`}
            style={mode !== "register" ? { background: "var(--gray-100)", color: "var(--gray-700)" } : {}}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                className="input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your name"
              />
            </div>
          )}
          <div className="form-group">
            <label>Username</label>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
            />
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", marginTop: 12 }}>
            {loading && <span className="spinner" />}
            {loading ? "Please wait..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthModal;
