/**
 * API client for communicating with the FastAPI backend.
 */
import axios from "axios";
import { STORAGE_KEYS } from "../constants/storage";

const API_BASE = process.env.REACT_APP_API_URL || "/api";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

// Add auth token to requests if available
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_KEYS.authToken);
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear stale auth so the UI reflects logged-out state
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(STORAGE_KEYS.authToken);
      localStorage.removeItem(STORAGE_KEYS.authUser);
      window.dispatchEvent(new Event("auth:logout"));
    }
    return Promise.reject(err);
  }
);

// -- Courses --

export async function fetchCourses(search = "", department = "", university = "") {
  const params = {};
  if (search) params.search = search;
  if (department) params.department = department;
  if (university) params.university = university;
  const res = await client.get("/courses/", { params });
  return res.data;
}

export async function fetchCourse(id) {
  const res = await client.get(`/courses/${id}`);
  return res.data;
}

export async function createCourse(data) {
  const res = await client.post("/courses/", data);
  return res.data;
}

export async function updateCourse(id, data) {
  const res = await client.put(`/courses/${id}`, data);
  return res.data;
}

export async function deleteCourse(id) {
  await client.delete(`/courses/${id}`);
}

export async function deleteCourseBulk(ids) {
  const res = await client.post("/courses/bulk-delete", { ids });
  return res.data;
}

export async function fetchDepartments() {
  const res = await client.get("/courses/departments");
  return res.data;
}

export async function fetchStoredUniversities() {
  const res = await client.get("/courses/universities");
  return res.data;
}

export async function fetchDashboardStats() {
  const res = await client.get("/courses/stats");
  return res.data;
}

// -- Comparison --

export async function compareText(text) {
  const res = await client.post("/compare/text", { text });
  return res.data;
}

export async function comparePdf(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await client.post("/compare/pdf", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function crossUniversityCompare(text, universityFilter = null, departmentFilter = null) {
  const res = await client.post("/compare/cross-university", {
    text,
    university_filter: universityFilter,
    department_filter: departmentFilter,
  });
  return res.data;
}

export async function fetchComparisonHistory(limit = 20) {
  const res = await client.get("/compare/history", { params: { limit } });
  return res.data;
}

export async function exportCsv(text) {
  const res = await client.post("/compare/export-csv", { text }, {
    responseType: "blob",
  });
  return res.data;
}

// -- Health --

export async function healthCheck() {
  const res = await client.get("/health");
  return res.data;
}

// -- Import --

export async function fetchUniversities() {
  const res = await client.get("/import/universities");
  return res.data;
}

export async function fetchDepartmentsForUni(universityCode) {
  const res = await client.get(`/import/${universityCode}/departments`);
  return res.data;
}

export async function previewCourses(universityCode, departmentCodes = null, limit = 5) {
  const res = await client.post(`/import/${universityCode}/preview`, null, {
    params: { department_codes: departmentCodes, limit },
  });
  return res.data;
}

export async function importCourses(universityCode, departmentCodes = null, limitPerDepartment = null) {
  const res = await client.post(`/import/${universityCode}/import`, null, {
    params: {
      department_codes: departmentCodes,
      limit_per_department: limitPerDepartment,
    },
  });
  return res.data;
}

// Backward compat
export const fetchGTUDepartments = () => fetchDepartmentsForUni("gtu");
export const previewGTUCourses = (depts, limit) => previewCourses("gtu", depts, limit);
export const importGTUCourses = (depts, limit) => importCourses("gtu", depts, limit);

// -- Auth --

export async function login(username, password) {
  const res = await client.post("/auth/login", { username, password });
  return res.data;
}

export async function register(username, password, fullName) {
  const res = await client.post("/auth/register", { username, password, full_name: fullName });
  return res.data;
}

export async function fetchCurrentUser() {
  const res = await client.get("/auth/me");
  return res.data;
}
