import React, { useState } from "react";
import { createCourse } from "../api/client";

const FIELDS = [
  { name: "code",       label: "Course Code *",    placeholder: "e.g. CS450",                       type: "text" },
  { name: "name",       label: "Course Name *",    placeholder: "e.g. Deep Learning",               type: "text" },
  { name: "university", label: "University",       placeholder: "e.g. Istanbul Technical University", type: "text" },
  { name: "faculty",    label: "Faculty",          placeholder: "e.g. Faculty of Engineering",       type: "text" },
  { name: "department", label: "Department",       placeholder: "e.g. Computer Science",             type: "text" },
  { name: "credits",    label: "ECTS Credits",     placeholder: "e.g. 6",                            type: "number" },
];

const EMPTY_FORM = { code: "", name: "", university: "", faculty: "", department: "", credits: "", description: "" };

function AddCourse() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.code || !form.name || form.description.length < 50) {
      setError("Course code, name, and a description of at least 50 characters are required.");
      return;
    }

    setLoading(true);
    try {
      const payload = { ...form, credits: form.credits ? parseInt(form.credits, 10) : null };
      const result = await createCourse(payload);
      setSuccess(
        `✓ Course "${result.code} — ${result.name}" added successfully with ${result.sections?.length || 0} sections indexed.`
      );
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add course.");
    } finally {
      setLoading(false);
    }
  };

  const descLen = form.description.length;
  const descOk  = descLen >= 50;

  return (
    <div className="card">
      <h2>Add New Course</h2>
      <form onSubmit={handleSubmit}>
        <div className="add-course-grid">
          {FIELDS.map(({ name, label, placeholder, type }) => (
            <div key={name}>
              <label className="add-course-label">{label}</label>
              <input
                name={name}
                className="input"
                value={form[name]}
                onChange={handleChange}
                placeholder={placeholder}
                type={type}
              />
            </div>
          ))}
        </div>

        <div style={{ marginBottom: 4 }}>
          <label className="add-course-label">Course Description / Syllabus *</label>
        </div>
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          placeholder="Paste the full course description including learning outcomes, weekly topics, required readings, and grading criteria…"
          style={{ minHeight: 180 }}
        />
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <span className={`char-counter ${descLen === 0 ? "" : descOk ? "ok" : "warn"}`}>
            {descLen} chars{descLen > 0 && !descOk ? ` — need ${50 - descLen} more` : descOk ? " ✓" : ""}
          </span>
        </div>

        {error   && <div className="error-msg" role="alert"><span>⚠</span> {error}</div>}
        {success && <div className="alert-success">{success}</div>}

        <div className="btn-row">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading
              ? <><span className="spinner" /> Adding…</>
              : "⊕ Add Course & Generate Embeddings"}
          </button>
          {(form.code || form.name || form.description) && !loading && (
            <button
              type="button"
              className="btn-sm btn-ghost"
              onClick={() => { setForm(EMPTY_FORM); setError(""); setSuccess(""); }}
            >
              Clear
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default AddCourse;
