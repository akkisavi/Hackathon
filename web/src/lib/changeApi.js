import { auth } from "./auth.js";

export const CHANGE_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");
export const API_ORIGIN = new URL(CHANGE_BASE, window.location.origin).origin;
export const isLoopback = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);

export const isShowcase = import.meta.env.VITE_ORBIT_SHOWCASE === "true";
export const hasDemoAccess = isLoopback || isShowcase;

export function imageUrl(path) {
  return new URL(path, API_ORIGIN).href;
}

export async function changeRequest(path, options = {}) {
  const token = auth.getToken();
  let response;
  try {
    response = await fetch(`${CHANGE_BASE}/change${path}`, {
      ...options,
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Cannot reach the analysis server. Please retry shortly.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Check the images and analysis settings, then try again.");
  }
  return response.json();
}

export function downloadJson(value, name) {
  downloadBlob(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }), name);
}

export function downloadImage(dataUrl, name) {
  const bytes = Uint8Array.from(atob(dataUrl.split(",")[1]), char => char.charCodeAt(0));
  downloadBlob(new Blob([bytes], { type: "image/png" }), name);
}

function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
