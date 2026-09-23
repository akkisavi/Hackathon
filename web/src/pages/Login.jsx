import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../lib/auth.js";
import ThemeToggle from "../components/ThemeToggle.jsx";

const BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const body = new URLSearchParams({ username: email, password });
      const res = await fetch(`${BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Invalid email or password");
      }
      const data = await res.json();
      auth.setToken(data.access_token);

      const meRes = await fetch(`${BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) auth.setUser(await meRes.json());

      navigate("/", { replace: true });
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative grid h-screen w-screen place-items-center overflow-hidden px-4">
      <ThemeToggle className="absolute right-5 top-5" />

      {/* corner telemetry chrome */}
      <div className="pointer-events-none absolute inset-6 hidden rounded-lg border border-zinc-200 dark:border-zinc-800/60 sm:block" />
      <div className="pointer-events-none absolute left-8 top-8 hidden font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-400 dark:text-zinc-600 sm:block">
        SIH26162 · NTRO-DM
      </div>
      <div className="pointer-events-none absolute bottom-8 right-8 hidden font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-400 dark:text-zinc-600 sm:block">
        Access restricted
      </div>

      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-7 shadow-xl shadow-zinc-200/50 dark:border-zinc-800 dark:bg-zinc-900/70 dark:shadow-[0_0_60px_-15px_rgba(34,211,238,0.25)] dark:backdrop-blur"
      >
        <div className="absolute inset-x-0 top-0 h-px overflow-hidden rounded-t-lg">
          <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-amber-500 to-transparent dark:via-cyan-400" style={{ animation: "scan 3s linear infinite" }} />
        </div>

        <div className="mb-6 flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full bg-amber-500 shadow-[0_0_10px_2px_rgba(245,158,11,0.6)] dark:bg-cyan-400 dark:shadow-[0_0_10px_2px_rgba(34,211,238,0.8)]" />
          <span className="font-display text-[13px] font-semibold uppercase tracking-[0.15em] text-zinc-900 dark:text-zinc-100">
            Thermal Source Monitor
          </span>
        </div>
        <h1 className="mb-6 text-[13px] text-zinc-500">Sign in to access mission systems</h1>

        <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-zinc-500">Email</label>
        <input
          type="email"
          required
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@agency.gov"
          className="mb-4 w-full rounded border border-zinc-300 bg-white px-3 py-2 text-[13px] text-zinc-900 placeholder:text-zinc-400 outline-none transition focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30 dark:border-zinc-700 dark:bg-zinc-950/60 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-cyan-500 dark:focus:ring-cyan-500/40"
        />

        <div className="mb-1.5 flex items-baseline justify-between">
          <label className="block text-[11px] font-medium uppercase tracking-wide text-zinc-500">Password</label>
          <button
            type="button"
            onClick={() => navigate("/forgot-password")}
            className="text-[11px] text-zinc-500 underline-offset-2 hover:underline dark:text-zinc-400"
          >
            Forgot password?
          </button>
        </div>
        <div className="mb-1.5 flex items-stretch gap-1.5">
          <input
            type={showPassword ? "text" : "password"}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-zinc-300 bg-white px-3 py-2 text-[13px] text-zinc-900 outline-none transition focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30 dark:border-zinc-700 dark:bg-zinc-950/60 dark:text-zinc-100 dark:focus:border-cyan-500 dark:focus:ring-cyan-500/40"
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            className="shrink-0 rounded border border-zinc-300 px-3 text-[11px] font-medium text-zinc-500 transition hover:border-zinc-400 hover:text-zinc-800 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-500 dark:hover:text-zinc-200"
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>

        <div className="mb-5 min-h-[1.1rem]">
          {error && (
            <p className="mt-1.5 flex items-center gap-1.5 text-[12px] text-red-600 dark:text-red-400">
              <span className="h-1 w-1 rounded-full bg-red-600 dark:bg-red-400" />
              {error}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="group relative w-full overflow-hidden rounded bg-zinc-900 px-3 py-2.5 text-[13px] font-semibold uppercase tracking-wide text-white transition hover:bg-zinc-800 disabled:cursor-wait disabled:opacity-60 dark:bg-cyan-500 dark:text-zinc-950 dark:hover:bg-cyan-400"
        >
          {loading ? "Authenticating…" : "Sign in"}
        </button>

        <p className="mt-5 text-center font-mono text-[10px] uppercase tracking-widest text-zinc-400 dark:text-zinc-700">
          No public registration · Admin-provisioned accounts only
        </p>
      </form>
    </div>
  );
}
