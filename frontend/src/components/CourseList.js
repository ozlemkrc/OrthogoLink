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
  const [selectedIds, setSelectedIds] = useState(new Set());
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

  const handleExpand = async (id) => {
    if (expandedId === id) { setExpandedId(null); setExpandedCourse(null); return; }
    try {
      const course = await fetchCourse(id);
      setExpandedCourse(course);
      setExpandedId(id);
    } catch {}
  };

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

      {/* Bulk actions */}
      {courses.length > 0 && (
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
            <div className="course-card" key={course.id}>
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
                      <input
                        type="checkbox"
                        checked={selectedIds.has(course.id)}
                        onChange={() => toggleSelect(course.id)}
                        onClick={(e) => e.stopPropagation()}
                        style={{ accentColor: "var(--primary)", width: 15, height: 15 }}
                      />
                      <span className="code">{course.code}</span>
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="btn-sm btn-ghost" onClick={() => handleExpand(course.id)}>
                        {expandedId === course.id ? "▲" : "▼"}
                      </button>
                      <button className="btn-sm btn-ghost" onClick={() => handleEdit(course)}>✎</button>
                      <button
                        className="btn-sm btn-ghost"
                        style={{ color: "var(--danger)", borderColor: "transparent" }}
                        onClick={() => handleDelete(course.id, course.code)}
                      >
                        ✕
                      </button>
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

                  {expandedId === course.id && expandedCourse && (
                    <div className="course-detail">
                      <div className="detail-label">
                        {expandedCourse.university || "Unknown University"}
                        {expandedCourse.faculty ? ` / ${expandedCourse.faculty}` : ""}
                      </div>
                      <div className="detail-label" style={{ marginTop: 10 }}>
                        Sections ({expandedCourse.sections?.length || 0})
                      </div>
                      {expandedCourse.sections?.map((sec) => (
                        <div key={sec.id} className="section-item">
                          <strong>{sec.heading}</strong>
                          <p>{sec.content.substring(0, 200)}{sec.content.length > 200 ? "…" : ""}</p>
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
