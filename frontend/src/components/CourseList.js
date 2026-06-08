import React, { useEffect, useState, useCallback } from "react";
import {
  fetchCourses,
  deleteCourse,
  deleteCourseBulk,
  fetchDepartments,
  fetchStoredUniversities,
  fetchCourse,
  updateCourse,
} from "../api/client";

function CourseList({ isAdmin = false }) {
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
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

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
    setSelectedIds(new Set());
    setSelectionMode(false);
  }, [loadCourses]);

  useEffect(() => {
    fetchDepartments().then((d) => setDepartments(d.departments || [])).catch(() => {});
    fetchStoredUniversities().then((d) => setUniversities(d.universities || [])).catch(() => {});
  }, []);

  const handleDelete = async (id, code) => {
    if (!window.confirm(`Delete course ${code}? This will rebuild the FAISS index.`)) return;
    try {
      setError("");
      await deleteCourse(id);
      await loadCourses();
    } catch (err) {
      setError(err?.response?.data?.detail || "Delete failed. Please try again.");
    }
  };

  const toggleSelect = (id) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  // Clicking a card (admin only) enters selection mode and toggles that card.
  const handleCardClick = (course) => {
    if (!isAdmin || editingCourse?.id === course.id) return;
    setSelectionMode(true);
    toggleSelect(course.id);
  };

  const exitSelection = () => {
    setSelectionMode(false);
    setSelectedIds(new Set());
  };

  const toggleSelectAll = () =>
    setSelectedIds(
      selectedIds.size === courses.length ? new Set() : new Set(courses.map((c) => c.id))
    );

  const handleBulkDelete = async () => {
    if (!selectedIds.size) return;
    if (!window.confirm(`Delete ${selectedIds.size} selected course(s)? This will rebuild the FAISS index.`)) return;
    setBulkDeleting(true);
    try {
      setError("");
      await deleteCourseBulk([...selectedIds]);
      setSelectedIds(new Set());
      await loadCourses();
    } catch (err) {
      setError(err?.response?.data?.detail || "Bulk delete failed.");
    }
    setBulkDeleting(false);
  };

  const openDetail = async (id) => {
    try {
      const course = await fetchCourse(id);
      setExpandedCourse(course);
      setExpandedId(id);
    } catch {}
  };

  const closeDetail = useCallback(() => {
    setExpandedId(null);
    setExpandedCourse(null);
  }, []);

  // Close the detail overlay on Escape while it is open.
  useEffect(() => {
    if (!expandedId) return;
    const onKey = (e) => { if (e.key === "Escape") closeDetail(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expandedId, closeDetail]);

  const handleEdit = (course) =>
    setEditingCourse({
      id: course.id,
      name: course.name || "",
      university: course.university || "",
      faculty: course.faculty || "",
      department: course.department || "",
      credits: course.credits || "",
    });

  const handleSaveEdit = async () => {
    if (!editingCourse) return;
    try {
      await updateCourse(editingCourse.id, {
        name:       editingCourse.name       || undefined,
        university: editingCourse.university || undefined,
        faculty:    editingCourse.faculty    || undefined,
        department: editingCourse.department || undefined,
        credits:    editingCourse.credits ? parseInt(editingCourse.credits, 10) : undefined,
      });
      setEditingCourse(null);
      loadCourses();
    } catch {}
  };

  const hasFilters = search || departmentFilter || universityFilter;

  return (
    <>
      {/* Search & Filter */}
      <div className="card" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", padding: "14px 18px" }}>
        <div className="search-wrap">
          <span className="search-icon">⊙</span>
          <input
            className="input"
            placeholder="Search by code, name, university, department…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input"
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
          style={{ width: "auto", minWidth: 170, flexShrink: 0 }}
        >
          <option value="">All Departments</option>
          {departments.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          className="input"
          value={universityFilter}
          onChange={(e) => setUniversityFilter(e.target.value)}
          style={{ width: "auto", minWidth: 200, flexShrink: 0 }}
        >
          <option value="">All Universities</option>
          {universities.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
        {hasFilters && (
          <button
            className="btn-sm btn-ghost"
            onClick={() => { setSearch(""); setDepartmentFilter(""); setUniversityFilter(""); }}
          >
            ✕ Clear
          </button>
        )}
        <div style={{ color: "var(--text-secondary)", fontSize: "0.82rem", marginLeft: "auto", whiteSpace: "nowrap" }}>
          {courses.length} course{courses.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Bulk actions — only shown once a card has been clicked (selection mode) */}
      {isAdmin && selectionMode && courses.length > 0 && (
        <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 18px" }}>
          <input
            type="checkbox"
            checked={selectedIds.size === courses.length && courses.length > 0}
            ref={(el) => { if (el) el.indeterminate = selectedIds.size > 0 && selectedIds.size < courses.length; }}
            onChange={toggleSelectAll}
            title="Select all"
            style={{ accentColor: "var(--primary)", width: 16, height: 16 }}
          />
          <span style={{ fontSize: "0.83rem", color: "var(--text-secondary)" }}>
            {selectedIds.size > 0 ? `${selectedIds.size} selected` : "Select all"}
          </span>
          {selectedIds.size > 0 && (
            <button
              className="btn-sm btn-danger"
              style={{ marginLeft: 4 }}
              onClick={handleBulkDelete}
              disabled={bulkDeleting}
            >
              {bulkDeleting ? "Deleting…" : `✕ Delete ${selectedIds.size}`}
            </button>
          )}
          <button className="btn-sm btn-ghost" style={{ marginLeft: "auto" }} onClick={exitSelection}>
            Done
          </button>
        </div>
      )}

      {error && <div className="error-msg"><span>⚠</span> {error}</div>}

      {loading ? (
        <div className="card">
          <div className="loading-state">
            <div className="spinner-lg" />
            <p>Loading courses…</p>
          </div>
        </div>
      ) : courses.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">📚</span>
            <h3>No courses found</h3>
            <p>
              {hasFilters
                ? "Try adjusting your search or filters."
                : "Import or add courses to get started."}
            </p>
          </div>
        </div>
      ) : (
        <div className="course-grid">
          {courses.map((course) => (
            <div
              className="course-card"
              key={course.id}
              onClick={() => handleCardClick(course)}
              style={{
                cursor: isAdmin && editingCourse?.id !== course.id ? "pointer" : "default",
                ...(selectionMode && selectedIds.has(course.id)
                  ? { borderColor: "var(--primary)", boxShadow: "0 0 0 1px var(--primary)" }
                  : {}),
              }}
            >
              {editingCourse?.id === course.id ? (
                <EditForm
                  form={editingCourse}
                  onChange={(field, val) => setEditingCourse({ ...editingCourse, [field]: val })}
                  onSave={handleSaveEdit}
                  onCancel={() => setEditingCourse(null)}
                />
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {isAdmin && selectionMode && (
                        <input
                          type="checkbox"
                          checked={selectedIds.has(course.id)}
                          onChange={() => toggleSelect(course.id)}
                          onClick={(e) => e.stopPropagation()}
                          style={{ accentColor: "var(--primary)", width: 15, height: 15 }}
                        />
                      )}
                      <span className="code">{course.code}</span>
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        className="btn-sm btn-ghost"
                        onClick={(e) => { e.stopPropagation(); openDetail(course.id); }}
                        title="View details"
                      >
                        Details
                      </button>
                      {isAdmin && selectionMode && (
                        <>
                          <button
                            className="btn-sm btn-ghost"
                            onClick={(e) => { e.stopPropagation(); handleEdit(course); }}
                          >
                            ✎
                          </button>
                          <button
                            className="btn-sm btn-ghost"
                            style={{ color: "var(--danger)", borderColor: "transparent" }}
                            onClick={(e) => { e.stopPropagation(); handleDelete(course.id, course.code); }}
                          >
                            ✕
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  <h3>{course.name}</h3>

                  {(course.university || course.faculty) && (
                    <div className="dept" style={{ marginTop: 4 }}>
                      {course.university || "Unknown University"}
                      {course.faculty ? ` / ${course.faculty}` : ""}
                    </div>
                  )}
                  {course.department && <div className="dept">{course.department}</div>}
                  {course.credits && (
                    <div className="dept" style={{ marginTop: 4 }}>
                      <span style={{
                        background: "var(--primary-light)",
                        color: "var(--primary)",
                        padding: "1px 7px",
                        borderRadius: 999,
                        fontWeight: 700,
                        fontSize: "0.75rem",
                      }}>
                        {course.credits} ECTS
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Course detail overlay — opened from a card's "Details" button */}
      {expandedId && expandedCourse && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div
            className="modal"
            style={{ maxWidth: 600, maxHeight: "85vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header" style={{ marginBottom: 16, alignItems: "flex-start" }}>
              <div>
                <span className="code">{expandedCourse.code}</span>
                <div className="modal-title" style={{ marginTop: 6 }}>{expandedCourse.name}</div>
              </div>
              <button className="modal-close" onClick={closeDetail} title="Close (Esc)">✕</button>
            </div>

            <div style={{ overflowY: "auto" }}>
              <div className="detail-label">
                {expandedCourse.university || "Unknown University"}
                {expandedCourse.faculty ? ` / ${expandedCourse.faculty}` : ""}
              </div>
              {expandedCourse.department && (
                <div className="dept" style={{ marginBottom: 6 }}>{expandedCourse.department}</div>
              )}
              {expandedCourse.credits && (
                <div className="dept" style={{ marginBottom: 12 }}>
                  <span style={{
                    background: "var(--primary-light)",
                    color: "var(--primary)",
                    padding: "1px 7px",
                    borderRadius: 999,
                    fontWeight: 700,
                    fontSize: "0.75rem",
                  }}>
                    {expandedCourse.credits} ECTS
                  </span>
                </div>
              )}

              <div className="detail-label" style={{ marginTop: 10 }}>
                Sections ({expandedCourse.sections?.length || 0})
              </div>
              {expandedCourse.sections?.map((sec) => (
                <div key={sec.id} className="section-item">
                  <strong>{sec.heading}</strong>
                  <p style={{ whiteSpace: "pre-wrap" }}>{sec.content}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function EditForm({ form, onChange, onSave, onCancel }) {
  const fields = [
    { field: "name",       placeholder: "Course Name" },
    { field: "department", placeholder: "Department" },
    { field: "university", placeholder: "University" },
    { field: "faculty",    placeholder: "Faculty" },
  ];
  return (
    <div>
      {fields.map(({ field, placeholder }) => (
        <input
          key={field}
          className="input"
          value={form[field]}
          onChange={(e) => onChange(field, e.target.value)}
          placeholder={placeholder}
          style={{ marginBottom: 6, width: "100%" }}
        />
      ))}
      <input
        className="input"
        type="number"
        value={form.credits}
        onChange={(e) => onChange("credits", e.target.value)}
        placeholder="ECTS Credits"
        style={{ marginBottom: 10, width: "100%" }}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <button className="btn-sm btn-primary" onClick={onSave}>✓ Save</button>
        <button className="btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default CourseList;
