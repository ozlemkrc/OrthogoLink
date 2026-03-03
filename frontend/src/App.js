import React, { useState } from "react";
import UploadForm from "./components/UploadForm";
import ResultsDisplay from "./components/ResultsDisplay";
import CourseList from "./components/CourseList";
import AddCourse from "./components/AddCourse";

function App() {
  const [activeTab, setActiveTab] = useState("compare");
  const [results, setResults] = useState(null);

  return (
    <div className="app-container">
      <header className="header">
        <h1>Curriculum Orthogonality Checker</h1>
        <p>AI-powered course syllabus overlap detection system</p>
      </header>

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
      </nav>

      {activeTab === "compare" && (
        <>
          <UploadForm onResult={setResults} />
          {results && <ResultsDisplay data={results} />}
        </>
      )}

      {activeTab === "courses" && <CourseList />}

      {activeTab === "add" && <AddCourse />}
    </div>
  );
}

export default App;
