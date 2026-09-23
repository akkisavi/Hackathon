import { auth } from "./auth.js";

const BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

function authHeaders(extra = {}) {
  const token = auth.getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

function handle401(res) {
  if (res.status === 401) {
    auth.clear();
    window.location.href = "/login";
  }
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  handle401(res);
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json();
}

export const api = {
  me: () => get(`/auth/me`),
  myApiKeys: () => get(`/auth/me/api-keys`),
  changePassword: (body) =>
    fetch(`${BASE}/auth/change-password`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    }).then(async (res) => {
      handle401(res);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail ?? `API ${res.status}`);
      return data;
    }),
  sources: (params = {}) => get(`/sources/${qs(params)}`),
  source: (id) => get(`/sources/${id}`),
  infra: (params = {}) => get(`/infra/${qs(params)}`),
  infraCounts: () => get(`/infra/counts`),
  alerts: (params = {}) => get(`/alerts/${qs(params)}`),
  sendAlert: (id) =>
    fetch(`${BASE}/alerts/${id}/notify`, { method: "POST", headers: authHeaders() }).then(async (res) => {
      handle401(res);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail ?? `API ${res.status}`);
      return data;
    }),
  query: async (q) => {
    const res = await fetch(`${BASE}/query/`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ q }),
    });
    handle401(res);
    if (!res.ok) throw new Error((await res.json())?.detail ?? `API ${res.status}`);
    return res.json();
  },
  exportUrl: (params = {}) => `${BASE}/export/${qs(params)}`,
};

async function adminRequest(method, path, body) {
  const res = await fetch(`${BASE}/admin${path}`, {
    method,
    headers: authHeaders(body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined,
  });
  handle401(res);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? `API ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

export const adminApi = {
  listUsers: () => adminRequest("GET", "/users"),
  createUser: (user) => adminRequest("POST", "/users", user),
  updateUser: (id, patch) => adminRequest("PUT", `/users/${id}`, patch),
  deleteUser: (id) => adminRequest("DELETE", `/users/${id}`),
  blockUser: (id) => adminRequest("POST", `/users/${id}/block`),
  unblockUser: (id) => adminRequest("POST", `/users/${id}/unblock`),
  generateApiKey: (id) => adminRequest("POST", `/users/${id}/api-keys`, {}),
  getUserApiKeys: (id) => adminRequest("GET", `/users/${id}/api-keys`),
};

function qs(params) {
  const e = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return e.length ? `?${new URLSearchParams(e)}` : "";
}
