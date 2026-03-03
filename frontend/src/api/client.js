/**
 * API client for communicating with the FastAPI backend.
 */
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "/api";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min (model inference can be slow first time)
});

// ── Courses ──────────────────────────────────────────────

export async function fetchCourses() {
  const res = await client.get("/courses/");
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

export async function deleteCourse(id) {
  await client.delete(`/courses/${id}`);
}

// ── Comparison ───────────────────────────────────────────

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

// ── Health ────────────────────────────────────────────────

export async function healthCheck() {
  const res = await client.get("/health");
  return res.data;
}
