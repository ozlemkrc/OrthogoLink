import React, { useEffect, useState, useCallback } from "react";
import UploadForm from "./components/UploadForm";
import ResultsDisplay from "./components/ResultsDisplay";
import CourseList from "./components/CourseList";
import AddCourse from "./components/AddCourse";
import ImportCourses from "./components/ImportCourses";
import Dashboard from "./components/Dashboard";
import ComparisonHistory from "./components/ComparisonHistory";
import AuthModal from "./components/AuthModal";
import StatusBar from "./components/StatusBar";
import { STORAGE_KEYS } from "./constants/storage";

const ALL_TABS = [
  { key: "dashboard",  label: "Dashboard",               icon: "⊞", adminOnly: false },
  { key: "compare",   label: "Compare Syllabus",         icon: "⊙", adminOnly: false },
  { key: "courses",   label: "Stored Courses",           icon: "≡", adminOnly: false },
  { key: "add",       label: "Add Course",               icon: "⊕", adminOnly: true  },
  { key: "import",    label: "Import from Universities", icon: "↓", adminOnly: true  },
  { key: "history",   label: "History",                  icon: "⏱", adminOnly: false },
];

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [results, setResults] = useState(null);
  const [user, setUser] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.theme);
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEYS.theme, theme);
  }, [theme]);

  useEffect(() => {
    const savedUser = localStorage.getItem(STORAGE_KEYS.authUser);
    const savedToken = localStorage.getItem(STORAGE_KEYS.authToken);
    if (savedUser && savedToken) {
      try { setUser(JSON.parse(savedUser)); } catch {}
    } else {
      localStorage.removeItem(STORAGE_KEYS.authUser);
      localStorage.removeItem(STORAGE_KEYS.authToken);
    }
  }, []);

  useEffect(() => {
    const handleForcedLogout = () => setUser(null);
    window.addEventListener("auth:logout", handleForcedLogout);
    return () => window.removeEventListener("auth:logout", handleForcedLogout);
  }, []);

  const toggleTheme = () => setTheme((prev) => (prev === "dark" ? "light" : "dark"));

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

  const isAdmin = user?.role === "admin";
  const TABS = ALL_TABS.filter((t) => !t.adminOnly || isAdmin);

  const handleTabChange = (key) => {
    setActiveTab(key);
    if (key !== "compare") setResults(null);
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-brand">
          <div className="header-logo" aria-hidden="true">⊞</div>
          <div>
            <h1>OrthogoLink</h1>
            <p>AI-powered curriculum orthogonality checker for Turkish universities</p>
          </div>
        </div>

        <div className="header-actions">
          {user ? (
            <div className="user-badge">
              <span className="user-name">{user.full_name || user.username}</span>
              <button className="btn-sm btn-ghost" onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <button className="btn-sm btn-ghost" onClick={() => setShowAuth(true)}>Login</button>
          )}
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === "dark" ? "☀ Light" : "☾ Dark"}
          </button>
        </div>
      </header>

      <StatusBar />

      <div className="tabs-wrapper">
        <nav className="tabs" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              className={`tab ${activeTab === tab.key ? "active" : ""}`}
              onClick={() => handleTabChange(tab.key)}
            >
              <span className="tab-icon" aria-hidden="true">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="tab-content" key={activeTab}>
        {activeTab === "dashboard" && <Dashboard />}

        {activeTab === "compare" && (
          <>
            <UploadForm onResult={setResults} />
            {results && <ResultsDisplay data={results} />}
          </>
        )}

        {activeTab === "courses"   && <CourseList />}
        {activeTab === "add"       && isAdmin && <AddCourse />}
        {activeTab === "import"    && isAdmin && <ImportCourses />}
        {activeTab === "history"   && <ComparisonHistory />}
      </div>

      {showAuth && (
        <AuthModal onLogin={handleLogin} onClose={() => setShowAuth(false)} />
      )}
    </div>
  );
}

export default App;
