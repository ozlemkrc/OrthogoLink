import React, { useEffect, useState } from "react";
import UploadForm from "./components/UploadForm";
import ResultsDisplay from "./components/ResultsDisplay";
import CourseList from "./components/CourseList";
import AddCourse from "./components/AddCourse";
import ImportCourses from "./components/ImportCourses";
import StatusBar from "./components/StatusBar";

function App() {
  const [activeTab, setActiveTab] = useState("compare");
  const [results, setResults] = useState(null);
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <div className="app-container">
      <header className="header">
        <div>
          <h1>Curriculum Orthogonality Checker</h1>
          <p>AI-powered course syllabus overlap detection system</p>
        </div>
        <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
        </button>
      </header>

      <StatusBar />

      <nav className="tabs">
        <button
          className={`tab ${activeTab === "compare" ? "active" : ""}`}
          onClick={() => setActiveTab("compare")}
        >
          Compare Syllabus
        </button>
        <button
          className={`tab ${activeTab === "courses" ? "active" : ""}`}
          onClick={() => setActiveTab("courses")}
        >
          Stored Courses
        </button>
        <button
          className={`tab ${activeTab === "add" ? "active" : ""}`}
          onClick={() => setActiveTab("add")}
        >
          Add Course
        </button>
        <button
          className={`tab ${activeTab === "import" ? "active" : ""}`}
          onClick={() => setActiveTab("import")}
        >
          Import from Universities
        </button>
      </nav>

      {activeTab === "compare" && (
        <>
          <UploadForm onResult={setResults} />
          {results && <ResultsDisplay data={results} />}
        </>
      )}

      {activeTab === "courses" && <CourseList />}

      {activeTab === "add" && <AddCourse />}

      {activeTab === "import" && <ImportCourses />}
    </div>
  );
}

export default App;
