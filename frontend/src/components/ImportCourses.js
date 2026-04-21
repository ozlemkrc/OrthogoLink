import React, { useEffect, useState } from "react";
import {
  fetchUniversities,
  fetchDepartmentsForUni,
  previewCourses,
  importCourses,
} from "../api/client";

function ImportCourses() {
  const [universities, setUniversities] = useState([]);
  const [selectedUni, setSelectedUni] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingDepts, setLoadingDepts] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [error, setError] = useState(null);
  const [limitPerDept, setLimitPerDept] = useState("");

  useEffect(() => {
    fetchUniversities()
      .then(setUniversities)
      .catch((err) => setError("Failed to load universities: " + err.message));
  }, []);

  const handleSelectUni = async (uni) => {
    setSelectedUni(uni);
    setDepartments([]);
    setSelectedDepartments([]);
    setPreviewData(null);
    setImportResult(null);
    setError(null);
    setLoadingDepts(true);
    try {
      const data = await fetchDepartmentsForUni(uni.code);
      setDepartments(data.departments || []);
    } catch (err) {
      setError("Failed to load departments: " + err.message);
    }
    setLoadingDepts(false);
  };

  const handleDepartmentToggle = (deptCode) => {
    setSelectedDepartments((prev) =>
      prev.includes(deptCode)
        ? prev.filter((d) => d !== deptCode)
        : [...prev, deptCode]
    );
  };

  const handleSelectAll = () => {
    if (selectedDepartments.length === departments.length) {
      setSelectedDepartments([]);
    } else {
      setSelectedDepartments(departments.map((d) => d.code));
    }
  };

  const handlePreview = async () => {
    if (!selectedUni) return;
    setLoading(true);
    setError(null);
    setPreviewData(null);
    setImportResult(null);

    try {
      const deptCodes = selectedDepartments.length > 0 ? selectedDepartments : null;
      const data = await previewCourses(selectedUni.code, deptCodes, 5);
      setPreviewData(data);
    } catch (err) {
      setError("Preview failed: " + (err.response?.data?.detail || err.message));
    }
    setLoading(false);
  };

  const handleImport = async () => {
    if (!selectedUni) return;
    if (!window.confirm(`Import courses from ${selectedUni.name}? This may take a while.`)) return;

    setLoading(true);
    setError(null);
    setImportResult(null);

    try {
      const deptCodes = selectedDepartments.length > 0 ? selectedDepartments : null;
      const limit = limitPerDept ? parseInt(limitPerDept) : null;
      const result = await importCourses(selectedUni.code, deptCodes, limit);
      setImportResult(result);
      setPreviewData(null);
    } catch (err) {
      setError("Import failed: " + (err.response?.data?.detail || err.message));
    }
    setLoading(false);
  };

  return (
    <div className="import-container">
      <div className="card">
        <h2>Import Courses from Universities</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 20 }}>
          Import course syllabi and ECTS forms from Turkish universities to build your comparison database.
        </p>

        {/* University Selection */}
        <div className="section">
          <h3>Select a University</h3>
          <div className="university-list">
            {universities.map((uni) => (
              <div
                key={uni.code}
                className={`university-card available ${selectedUni?.code === uni.code ? "selected-uni" : ""}`}
                onClick={() => handleSelectUni(uni)}
                style={{ cursor: "pointer" }}
              >
                <div>
                  <strong>{uni.name}</strong>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 2 }}>
                    {uni.code.toUpperCase()}
                  </div>
                </div>
                <span className="status" style={{ color: selectedUni?.code === uni.code ? "var(--primary)" : "var(--success)" }}>
                  {selectedUni?.code === uni.code ? "Selected" : "Available"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Department Selection */}
        {selectedUni && (
          <div className="section" style={{ marginTop: 30 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>{selectedUni.name} - Departments</h3>
              {departments.length > 0 && (
                <button className="btn-secondary" onClick={handleSelectAll} disabled={loading}>
                  {selectedDepartments.length === departments.length ? "Deselect All" : "Select All"}
                </button>
              )}
            </div>

            {loadingDepts ? (
              <div style={{ textAlign: "center", padding: 20 }}>
                <span className="spinner" style={{ borderColor: "var(--gray-300)", borderTopColor: "var(--primary)" }} />{" "}
                Loading departments...
              </div>
            ) : (
              <div className="department-grid">
                {departments.map((dept) => (
                  <label key={dept.code} className="checkbox-card">
                    <input
                      type="checkbox"
                      checked={selectedDepartments.includes(dept.code)}
                      onChange={() => handleDepartmentToggle(dept.code)}
                      disabled={loading}
                    />
                    <div>
                      <strong>{dept.code}</strong>
                      <span>{dept.name}</span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Import Options */}
        {selectedUni && departments.length > 0 && (
          <div className="section" style={{ marginTop: 30 }}>
            <h3>Import Options</h3>
            <div className="form-group">
              <label>Limit per Department (optional)</label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 5 (leave empty for all)"
                value={limitPerDept}
                onChange={(e) => setLimitPerDept(e.target.value)}
                disabled={loading}
                min="1"
                max="100"
              />
              <small style={{ color: "var(--text-secondary)" }}>
                Limit the number of courses imported per department
              </small>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {selectedUni && (
          <div className="button-group" style={{ marginTop: 30 }}>
            <button
              className="btn btn-secondary"
              onClick={handlePreview}
              disabled={loading || selectedDepartments.length === 0}
            >
              {loading && !importResult ? "Loading..." : "Preview Courses"}
            </button>
            <button
              className="btn btn-primary"
              onClick={handleImport}
              disabled={loading || selectedDepartments.length === 0}
            >
              {loading ? "Importing..." : "Import to Database"}
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="alert alert-error" style={{ marginTop: 20 }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Preview Results */}
        {previewData && (
          <div className="section" style={{ marginTop: 30 }}>
            <h3>Preview: {previewData.university || selectedUni?.name}</h3>
            <p style={{ color: "var(--text-secondary)", marginBottom: 15 }}>
              Found <strong>{previewData.total_courses}</strong> courses.
              Showing up to 20 below:
            </p>
            <div className="preview-list">
              {previewData.courses.map((course, idx) => (
                <div key={idx} className="preview-card">
                  <div className="course-header">
                    <span className="code">{course.code}</span>
                    <span className="credits">{course.credits} ECTS</span>
                  </div>
                  <h4>{course.name}</h4>
                  <p className="department">{course.department}</p>
                  <p className="description">
                    {course.description.substring(0, 200)}...
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Import Results */}
        {importResult && (
          <div className="section" style={{ marginTop: 30 }}>
            <div className="alert alert-success">
              <h3>Import Complete!</h3>
              <p>{importResult.message}</p>
              <div className="import-stats">
                <div className="stat">
                  <strong>{importResult.total_imported}</strong>
                  <span>Imported</span>
                </div>
                <div className="stat">
                  <strong>{importResult.total_skipped}</strong>
                  <span>Skipped</span>
                </div>
                <div className="stat">
                  <strong>{importResult.total_failed}</strong>
                  <span>Failed</span>
                </div>
              </div>
              {importResult.imported_courses.length > 0 && (
                <details style={{ marginTop: 15 }}>
                  <summary style={{ cursor: "pointer", color: "var(--primary)" }}>
                    View imported courses ({importResult.imported_courses.length})
                  </summary>
                  <div className="course-codes">
                    {importResult.imported_courses.join(", ")}
                  </div>
                </details>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ImportCourses;
