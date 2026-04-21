import React, { useState } from "react";
import { createCourse } from "../api/client";

function AddCourse() {
  const [form, setForm] = useState({
    code: "",
    name: "",
    university: "",
    faculty: "",
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
      setForm({
        code: "",
        name: "",
        university: "",
        faculty: "",
        department: "",
        credits: "",
        description: "",
      });
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
        <div className="add-course-grid">
          <div>
            <label className="add-course-label">
              Course Code *
            </label>
            <input
              name="code"
              className="input"
              value={form.code}
              onChange={handleChange}
              placeholder="e.g. CS450"
            />
          </div>
          <div>
            <label className="add-course-label">
              Course Name *
            </label>
            <input
              name="name"
              className="input"
              value={form.name}
              onChange={handleChange}
              placeholder="e.g. Deep Learning"
            />
          </div>
          <div>
            <label className="add-course-label">
              University
            </label>
            <input
              name="university"
              className="input"
              value={form.university}
              onChange={handleChange}
              placeholder="e.g. Istanbul Technical University"
            />
          </div>
          <div>
            <label className="add-course-label">
              Faculty
            </label>
            <input
              name="faculty"
              className="input"
              value={form.faculty}
              onChange={handleChange}
              placeholder="e.g. Faculty of Engineering"
            />
          </div>
          <div>
            <label className="add-course-label">
              Department
            </label>
            <input
              name="department"
              className="input"
              value={form.department}
              onChange={handleChange}
              placeholder="e.g. Computer Science"
            />
          </div>
          <div>
            <label className="add-course-label">
              ECTS Credits
            </label>
            <input
              name="credits"
              className="input"
              value={form.credits}
              onChange={handleChange}
              type="number"
              placeholder="e.g. 6"
            />
          </div>
        </div>

        <label className="add-course-label">
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
