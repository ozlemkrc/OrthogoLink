import React, { useEffect, useState, useCallback } from "react";
import {
  fetchCourses,
  deleteCourse,
  fetchDepartments,
  fetchStoredUniversities,
  fetchCourse,
  updateCourse,
} from "../api/client";

function CourseList() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [universityFilter, setUniversityFilter] = useState("");
  const [departments, setDepartments] = useState([]);
  const [universities, setUniversities] = useState([]);
  const [editingCourse, setEditingCourse] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [expandedCourse, setExpandedCourse] = useState(null);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchCourses(search, departmentFilter, universityFilter);
      setCourses(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load courses.");
    }
    setLoading(false);
  }, [search, departmentFilter, universityFilter]);

  useEffect(() => {
    loadCourses();
  }, [loadCourses]);

  useEffect(() => {
    fetchDepartments().then((data) => setDepartments(data.departments || [])).catch(() => {});
    fetchStoredUniversities().then((data) => setUniversities(data.universities || [])).catch(() => {});
  }, []);

  const handleDelete = async (id, code) => {
    if (!window.confirm(`Delete course ${code}? This will rebuild the FAISS index.`)) return;
    try {
      setError("");
      await deleteCourse(id);
      // Optimistically remove to avoid stale UI if refresh is slow.
      setCourses((prev) => prev.filter((c) => c.id !== id));
      await loadCourses();
    } catch (err) {
      setError(err?.response?.data?.detail || "Delete failed. Please try again.");
    }
  };

  const handleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedCourse(null);
      return;
    }
    try {
      const course = await fetchCourse(id);
      setExpandedCourse(course);
      setExpandedId(id);
    } catch {}
  };

  const handleEdit = async (course) => {
    setEditingCourse({
      id: course.id,
      name: course.name || "",
      university: course.university || "",
      faculty: course.faculty || "",
      department: course.department || "",
      credits: course.credits || "",
    });
  };

  const handleSaveEdit = async () => {
    if (!editingCourse) return;
    try {
      await updateCourse(editingCourse.id, {
        name: editingCourse.name || undefined,
        university: editingCourse.university || undefined,
        faculty: editingCourse.faculty || undefined,
        department: editingCourse.department || undefined,
        credits: editingCourse.credits ? parseInt(editingCourse.credits, 10) : undefined,
      });
      setEditingCourse(null);
      loadCourses();
    } catch {}
  };

  return (
    <>
      {/* Search and Filter Bar */}
      <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <input
            className="input"
            placeholder="Search by code, name, university, faculty, or department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
        <select
          className="input"
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
          style={{ width: "auto", minWidth: 180 }}
        >
          <option value="">All Departments</option>
          {departments.map((dept) => (
            <option key={dept} value={dept}>{dept}</option>
          ))}
        </select>
        <select
          className="input"
          value={universityFilter}
          onChange={(e) => setUniversityFilter(e.target.value)}
          style={{ width: "auto", minWidth: 220 }}
        >
          <option value="">All Universities</option>
          {universities.map((university) => (
            <option key={university} value={university}>{university}</option>
          ))}
        </select>
        <div style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
          {courses.length} course{courses.length !== 1 ? "s" : ""}
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <div className="spinner-lg" />
          <p style={{ marginTop: 12, color: "var(--text-secondary)" }}>Loading courses...</p>
        </div>
      ) : courses.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">&#128218;</div>
            <p>No courses found. {search || departmentFilter || universityFilter ? "Try adjusting your filters." : "Import or add courses to get started."}</p>
          </div>
        </div>
      ) : (
        <div className="course-grid">
          {courses.map((course) => (
            <div className="course-card" key={course.id}>
              {editingCourse && editingCourse.id === course.id ? (
                <div className="edit-form">
                  <input
                    className="input"
                    value={editingCourse.name}
                    onChange={(e) => setEditingCourse({ ...editingCourse, name: e.target.value })}
                    placeholder="Course Name"
                    style={{ marginBottom: 6, width: "100%" }}
                  />
                  <input
                    className="input"
                    value={editingCourse.department}
                    onChange={(e) => setEditingCourse({ ...editingCourse, department: e.target.value })}
                    placeholder="Department"
                    style={{ marginBottom: 6, width: "100%" }}
                  />
                  <input
                    className="input"
                    value={editingCourse.university}
                    onChange={(e) => setEditingCourse({ ...editingCourse, university: e.target.value })}
                    placeholder="University"
                    style={{ marginBottom: 6, width: "100%" }}
                  />
                  <input
                    className="input"
                    value={editingCourse.faculty}
                    onChange={(e) => setEditingCourse({ ...editingCourse, faculty: e.target.value })}
                    placeholder="Faculty"
                    style={{ marginBottom: 6, width: "100%" }}
                  />
                  <input
                    className="input"
                    type="number"
                    value={editingCourse.credits}
                    onChange={(e) => setEditingCourse({ ...editingCourse, credits: e.target.value })}
                    placeholder="Credits"
                    style={{ marginBottom: 8, width: "100%" }}
                  />
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="btn-sm btn-primary" onClick={handleSaveEdit}>Save</button>
                    <button className="btn-sm btn-ghost" onClick={() => setEditingCourse(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div className="code">{course.code}</div>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="btn-sm btn-ghost" onClick={() => handleExpand(course.id)} title="View details">
                        {expandedId === course.id ? "Hide" : "View"}
                      </button>
                      <button className="btn-sm btn-ghost" onClick={() => handleEdit(course)} title="Edit">
                        Edit
                      </button>
                      <button
                        className="btn-sm btn-ghost"
                        style={{ color: "var(--danger)" }}
                        onClick={() => handleDelete(course.id, course.code)}
                        title="Delete"
                      >
                        Del
                      </button>
                    </div>
                  </div>
                  <h3>{course.name}</h3>
                  {(course.university || course.faculty) && (
                    <div className="dept" style={{ marginTop: 2 }}>
                      {course.university || "Unknown University"}
                      {course.faculty ? ` / ${course.faculty}` : ""}
                    </div>
                  )}
                  {course.department && <div className="dept">{course.department}</div>}
                  {course.credits && (
                    <div className="dept" style={{ marginTop: 4 }}>{course.credits} ECTS</div>
                  )}
                  {expandedId === course.id && expandedCourse && (
                    <div className="course-detail">
                      <div className="detail-label" style={{ marginBottom: 6 }}>
                        Source: {expandedCourse.university || "Unknown University"}
                        {expandedCourse.faculty ? ` / ${expandedCourse.faculty}` : ""}
                      </div>
                      <div className="detail-label">Sections ({expandedCourse.sections?.length || 0})</div>
                      {expandedCourse.sections?.map((sec) => (
                        <div key={sec.id} className="section-item">
                          <strong>{sec.heading}</strong>
                          <p>{sec.content.substring(0, 200)}{sec.content.length > 200 ? "..." : ""}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default CourseList;
