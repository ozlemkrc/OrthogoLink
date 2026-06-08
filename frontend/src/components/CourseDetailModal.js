import React, { useEffect } from "react";

const ECTS_BADGE_STYLE = {
  background: "var(--primary-light)",
  color: "var(--primary)",
  padding: "1px 7px",
  borderRadius: 999,
  fontWeight: 700,
  fontSize: "0.75rem",
};

/**
 * Overlay showing a course's full details and sections.
 * Shared by the Stored Courses list and the comparison results view so both
 * surfaces present an identical detail view.
 *
 * @param {{ course: object|null, onClose: () => void }} props
 *   `course` is a full course object (code, name, university, faculty,
 *   department, credits, sections[]). When null, nothing renders.
 */
function CourseDetailModal({ course, onClose }) {
  // Close on Escape while the overlay is open.
  useEffect(() => {
    if (!course) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [course, onClose]);

  if (!course) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth: 600, maxHeight: "85vh", display: "flex", flexDirection: "column" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header" style={{ marginBottom: 16, alignItems: "flex-start" }}>
          <div>
            <span className="code">{course.code}</span>
            <div className="modal-title" style={{ marginTop: 6 }}>{course.name}</div>
          </div>
          <button className="modal-close" onClick={onClose} title="Close (Esc)">✕</button>
        </div>

        <div style={{ overflowY: "auto" }}>
          <div className="detail-label">
            {course.university || "Unknown University"}
            {course.faculty ? ` / ${course.faculty}` : ""}
          </div>
          {course.department && (
            <div className="dept" style={{ marginBottom: 6 }}>{course.department}</div>
          )}
          {course.credits && (
            <div className="dept" style={{ marginBottom: 12 }}>
              <span style={ECTS_BADGE_STYLE}>{course.credits} ECTS</span>
            </div>
          )}

          {course.description && !course.sections?.length && (
            <div className="section-item">
              <p style={{ whiteSpace: "pre-wrap" }}>{course.description}</p>
            </div>
          )}

          {course.sections?.length > 0 && (
            <>
              <div className="detail-label" style={{ marginTop: 10 }}>
                Sections ({course.sections.length})
              </div>
              {course.sections.map((sec) => (
                <div key={sec.id} className="section-item">
                  <strong>{sec.heading}</strong>
                  <p style={{ whiteSpace: "pre-wrap" }}>{sec.content}</p>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default CourseDetailModal;
