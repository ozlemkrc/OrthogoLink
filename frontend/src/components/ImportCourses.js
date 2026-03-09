import React, { useEffect, useState } from "react";
import { 
  fetchUniversities, 
  fetchGTUDepartments, 
  previewGTUCourses, 
  importGTUCourses 
} from "../api/client";

function ImportCourses() {
  const [universities, setUniversities] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [error, setError] = useState(null);
  const [limitPerDept, setLimitPerDept] = useState("");

  useEffect(() => {
    // Load universities on mount
    fetchUniversities()
      .then(setUniversities)
      .catch((err) => setError("Failed to load universities: " + err.message));

    // Load GTU departments
    fetchGTUDepartments()
      .then((data) => setDepartments(data.departments || []))
      .catch((err) => setError("Failed to load departments: " + err.message));
  }, []);

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
    setLoading(true);
    setError(null);
    setPreviewData(null);
    setImportResult(null);

    try {
      const deptCodes = selectedDepartments.length > 0 ? selectedDepartments : null;
      const data = await previewGTUCourses(deptCodes, 5);
      setPreviewData(data);
    } catch (err) {
      setError("Preview failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!window.confirm("Are you sure you want to import these courses? This may take a while.")) {
      return;
    }

    setLoading(true);
    setError(null);
    setImportResult(null);

    try {
      const deptCodes = selectedDepartments.length > 0 ? selectedDepartments : null;
      const limit = limitPerDept ? parseInt(limitPerDept) : null;
      const result = await importGTUCourses(deptCodes, limit);
      setImportResult(result);
      setPreviewData(null); // Clear preview after import
    } catch (err) {
      setError("Import failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="import-container">
      <div className="card">
        <h2>📚 Import Courses from Universities</h2>
        <p style={{ color: "var(--gray-500)", marginBottom: 20 }}>
          Import course syllabi and ECTS forms from Turkish universities to build your comparison database.
        </p>

        {/* University Selection */}
        <div className="section">
          <h3>Available Universities</h3>
          <div className="university-list">
            {universities.map((uni) => (
              <div
                key={uni.code}
                className={`university-card ${uni.available ? "available" : "unavailable"}`}
              >
                <strong>{uni.name}</strong>
                <span className="status">
                  {uni.available ? "✓ Available" : "🔜 Coming Soon"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* GTU Department Selection */}
        <div className="section" style={{ marginTop: 30 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>GTÜ Departments</h3>
            <button 
              className="btn-secondary" 
              onClick={handleSelectAll}
              disabled={loading}
            >
              {selectedDepartments.length === departments.length ? "Deselect All" : "Select All"}
            </button>
          </div>
          
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

          {departments.length === 0 && (
            <p style={{ color: "var(--gray-500)", textAlign: "center", padding: 20 }}>
              No departments available
            </p>
          )}
        </div>

        {/* Import Options */}
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
            <small style={{ color: "var(--gray-500)" }}>
              Limit the number of courses imported per department (useful for testing)
            </small>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="button-group" style={{ marginTop: 30 }}>
          <button
            className="btn-secondary"
            onClick={handlePreview}
            disabled={loading || selectedDepartments.length === 0}
          >
            {loading ? "Loading..." : "Preview Courses"}
          </button>
          <button
            className="btn-primary"
            onClick={handleImport}
            disabled={loading || selectedDepartments.length === 0}
          >
            {loading ? "Importing..." : "Import to Database"}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="alert alert-error" style={{ marginTop: 20 }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Preview Results */}
        {previewData && (
          <div className="section" style={{ marginTop: 30 }}>
            <h3>Preview Results</h3>
            <p style={{ color: "var(--gray-600)", marginBottom: 15 }}>
              Found <strong>{previewData.total_courses}</strong> courses total. 
              Showing first 10 below:
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
                    {course.description.substring(0, 150)}...
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
              <h3>✓ Import Complete!</h3>
              <p>{importResult.message}</p>
              <div className="import-stats">
                <div className="stat">
                  <strong>{importResult.total_imported}</strong>
                  <span>Imported</span>
                </div>
                <div className="stat">
                  <strong>{importResult.total_failed}</strong>
                  <span>Failed/Skipped</span>
                </div>
              </div>
              {importResult.imported_courses.length > 0 && (
                <details style={{ marginTop: 15 }}>
                  <summary style={{ cursor: "pointer", color: "var(--primary)" }}>
                    View imported course codes ({importResult.imported_courses.length})
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
