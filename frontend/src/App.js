import React, { useEffect, useState, useCallback } from "react";
import UploadForm from "./components/UploadForm";
import ResultsDisplay from "./components/ResultsDisplay";
import CourseList from "./components/CourseList";
import AddCourse from "./components/AddCourse";
import ImportCourses from "./components/ImportCourses";
import Dashboard from "./components/Dashboard";
import CrossUniCompare from "./components/CrossUniCompare";
import ComparisonHistory from "./components/ComparisonHistory";
import AuthModal from "./components/AuthModal";
import StatusBar from "./components/StatusBar";
import { STORAGE_KEYS } from "./constants/storage";

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [results, setResults] = useState(null);
  const [user, setUser] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.theme);
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEYS.theme, theme);
  }, [theme]);

  // Restore auth state
  useEffect(() => {
    const savedUser = localStorage.getItem(STORAGE_KEYS.authUser);
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {}
    }
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const handleLogin = useCallback((userData) => {
    setUser(userData);
    localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(userData));
    localStorage.setItem(STORAGE_KEYS.authToken, userData.access_token);
    setShowAuth(false);
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEYS.authUser);
    localStorage.removeItem(STORAGE_KEYS.authToken);
  }, []);

  const tabs = [
    { key: "dashboard", label: "Dashboard" },
    { key: "compare", label: "Compare Syllabus" },
    { key: "cross-uni", label: "Cross-University" },
    { key: "courses", label: "Stored Courses" },
    { key: "add", label: "Add Course" },
    { key: "import", label: "Import from Universities" },
    { key: "history", label: "History" },
  ];

  return (
    <div className="app-container">
      <header className="header">
        <div>
          <h1>OrthogoLink</h1>
          <p>AI-powered curriculum orthogonality checker for Turkish universities</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {user ? (
            <div className="user-badge">
              <span className="user-name">{user.full_name || user.username}</span>
              <button className="btn-sm btn-ghost" onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <button className="btn-sm btn-ghost" onClick={() => setShowAuth(true)}>Login</button>
          )}
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <StatusBar />

      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "dashboard" && <Dashboard />}

      {activeTab === "compare" && (
        <>
          <UploadForm onResult={setResults} />
          {results && <ResultsDisplay data={results} />}
        </>
      )}

      {activeTab === "cross-uni" && <CrossUniCompare />}

      {activeTab === "courses" && <CourseList />}

      {activeTab === "add" && <AddCourse />}

      {activeTab === "import" && <ImportCourses />}

      {activeTab === "history" && <ComparisonHistory />}

      {showAuth && (
        <AuthModal onLogin={handleLogin} onClose={() => setShowAuth(false)} />
      )}
    </div>
  );
}

export default App;
