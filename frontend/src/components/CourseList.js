import React, { useEffect, useState } from "react";
import { fetchCourses } from "../api/client";

function CourseList() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCourses()
      .then((data) => setCourses(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <span className="spinner" style={{ borderColor: "var(--gray-300)", borderTopColor: "var(--primary)" }} />{" "}
        Loading courses...
      </div>
    );
  }

  if (courses.length === 0) {
    return (
      <div className="card">
        <p style={{ color: "var(--gray-500)" }}>
          No courses stored yet. Add some from the "Add Course" tab.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="card">
        <h2>Stored Courses ({courses.length})</h2>
      </div>
      <div className="course-grid">
        {courses.map((course) => (
          <div className="course-card" key={course.id}>
            <div className="code">{course.code}</div>
            <h3>{course.name}</h3>
            {course.department && <div className="dept">{course.department}</div>}
            {course.credits && (
              <div className="dept" style={{ marginTop: 4 }}>
                {course.credits} ECTS
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export default CourseList;
