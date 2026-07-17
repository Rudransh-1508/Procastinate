// Thin fetch wrapper around the backend API (proxied at /api during dev).
// Attaches the bearer token from localStorage to every request; on 401
// (expired/invalid session) it clears the token and asks the app to bounce
// to /login via a custom event (AuthContext doesn't poll — it reacts to this).
const BASE = "/api";
const TOKEN_KEY = "profiler_token";

async function request(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new CustomEvent("profiler:unauthorized"));
    throw new Error("401: session expired");
  }
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
  completeTask: (taskId) => request(`/tasks/${taskId}/complete`, { method: "POST" }),
  logEvent: (event) => request("/events", { method: "POST", body: JSON.stringify(event) }),
  sync: () => request("/sync", { method: "POST" }),
  startSession: (text) => request("/sessions/start", { method: "POST", body: JSON.stringify({ text }) }),
  closeoutSession: (id, text) =>
    request(`/sessions/${id}/closeout`, { method: "POST", body: JSON.stringify({ text }) }),
  sessions: (limit = 50) => request(`/sessions?limit=${limit}`),
  activeSession: () => request("/sessions/active"),
  productivityInsights: () => request("/insights/productivity"),
};

export const googleAuthorizeUrl = () => `${BASE}/auth/google/authorize`;
