const BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json();
}

export const api = {
  sources: (params = {}) => get(`/sources/${qs(params)}`),
  source: (id) => get(`/sources/${id}`),
  infra: (params = {}) => get(`/infra/${qs(params)}`),
  infraCounts: () => get(`/infra/counts`),
  alerts: (params = {}) => get(`/alerts/${qs(params)}`),
  query: async (q) => {
    const res = await fetch(`${BASE}/query/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q }),
    });
    if (!res.ok) throw new Error((await res.json())?.detail ?? `API ${res.status}`);
    return res.json();
  },
  exportUrl: (params = {}) => `${BASE}/export/${qs(params)}`,
};

function qs(params) {
  const e = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return e.length ? `?${new URLSearchParams(e)}` : "";
}
