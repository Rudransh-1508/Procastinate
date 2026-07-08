// Thin fetch wrapper around the backend API (proxied at /api during dev).
const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  status: () => request("/status"),
  dashboard: () => request("/dashboard"),
  profile: () => request("/profile"),
  refreshProfile: () => request("/profile/refresh", { method: "POST" }),
  tasks: (status) => request(`/tasks${status ? `?status=${status}` : ""}`),
  events: (limit = 100) => request(`/events?limit=${limit}`),
  insights: () => request("/insights"),
  checkinPrompt: (type = "morning") => request(`/checkin/prompt?checkin_type=${type}`),
  submitCheckin: (text, checkin_type = "manual") =>
    request("/checkin", { method: "POST", body: JSON.stringify({ text, checkin_type }) }),
  query: (message, conversation_history = []) =>
    request("/query", {
      method: "POST",
      body: JSON.stringify({ message, conversation_history }),
    }),
  weeklyReport: () => request("/report/weekly"),
  addTask: (task) => request("/tasks", { method: "POST", body: JSON.stringify(task) }),
  logEvent: (event) => request("/events", { method: "POST", body: JSON.stringify(event) }),
  sync: () => request("/sync", { method: "POST" }),
};
