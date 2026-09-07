const BASE =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function get(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export const api = {
  sources: () => get(`/sources/`),
  source: (id) => get(`/sources/${id}`),
  alerts: () => get(`/alerts/`),
};
