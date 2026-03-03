import React, { useState } from "react";
import { createCourse } from "../api/client";

function AddCourse() {
  const [form, setForm] = useState({
    code: "",
    name: "",
    department: "",
    credits: "",
    description: "",
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.code || !form.name || form.description.length < 50) {
      setError("Code, name, and a description of at least 50 characters are required.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        ...form,
        credits: form.credits ? parseInt(form.credits, 10) : null,
      };
      const result = await createCourse(payload);
      setSuccess(`Course "${result.code} — ${result.name}" added successfully with ${result.sections?.length || 0} sections.`);
      setForm({ code: "", name: "", department: "", credits: "", description: "" });
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add course");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Add New Course</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
          <div>
            <label style={{ fontSize: "0.85rem", fontWeight: 500, display: "block", marginBottom: 4 }}>
              Course Code *
            </label>
            <input
              name="code"
              value={form.code}
              onChange={handleChange}
              placeholder="e.g. CS450"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid var(--gray-300)",
                borderRadius: "var(--radius)",
                fontSize: "0.9rem",
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: "0.85rem", fontWeight: 500, display: "block", marginBottom: 4 }}>
              Course Name *
            </label>
            <input
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="e.g. Deep Learning"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid var(--gray-300)",
                borderRadius: "var(--radius)",
                fontSize: "0.9rem",
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: "0.85rem", fontWeight: 500, display: "block", marginBottom: 4 }}>
              Department
            </label>
            <input
              name="department"
              value={form.department}
              onChange={handleChange}
              placeholder="e.g. Computer Science"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid var(--gray-300)",
                borderRadius: "var(--radius)",
                fontSize: "0.9rem",
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: "0.85rem", fontWeight: 500, display: "block", marginBottom: 4 }}>
              ECTS Credits
            </label>
            <input
              name="credits"
              value={form.credits}
              onChange={handleChange}
              type="number"
              placeholder="e.g. 6"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid var(--gray-300)",
                borderRadius: "var(--radius)",
                fontSize: "0.9rem",
              }}
            />
          </div>
        </div>

        <label style={{ fontSize: "0.85rem", fontWeight: 500, display: "block", marginBottom: 4 }}>
          Course Description / Syllabus *
        </label>
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          placeholder="Paste the full course description including learning outcomes, content, schedule..."
          style={{ minHeight: 180 }}
        />

        {error && <div className="error-msg">{error}</div>}
        {success && (
          <div className="alert-success">{success}</div>
        )}

        <div className="btn-row">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Adding..." : "Add Course & Generate Embeddings"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default AddCourse;
