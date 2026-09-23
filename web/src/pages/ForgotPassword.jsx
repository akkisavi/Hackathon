import { useState } from "react";
import { Link } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle.jsx";

const BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Something went wrong");
      }
      setSent(true);
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative grid h-screen w-screen place-items-center overflow-hidden px-4">
      <ThemeToggle className="absolute right-5 top-5" />

      <div className="relative w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-7 shadow-xl shadow-zinc-200/50 dark:border-zinc-800 dark:bg-zinc-900/70">
        <h1 className="mb-2 font-display text-[13px] font-semibold uppercase tracking-[0.15em] text-zinc-900 dark:text-zinc-100">
          Reset password
        </h1>

        {sent ? (
          <p className="text-[13px] text-zinc-600 dark:text-zinc-400">
            If an account exists for <span className="font-medium">{email}</span>, reset
            instructions are on their way.
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <p className="mb-5 text-[13px] text-zinc-500">
              Enter your account email and we'll send you a reset link.
            </p>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-zinc-500">
              Email
            </label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@agency.gov"
              className="mb-4 w-full rounded border border-zinc-300 bg-white px-3 py-2 text-[13px] text-zinc-900 placeholder:text-zinc-400 outline-none transition focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30 dark:border-zinc-700 dark:bg-zinc-950/60 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-cyan-500 dark:focus:ring-cyan-500/40"
            />

            {error && (
              <p className="mb-4 text-[12px] text-red-600 dark:text-red-400">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded bg-zinc-900 px-3 py-2.5 text-[13px] font-semibold uppercase tracking-wide text-white transition hover:bg-zinc-800 disabled:cursor-wait disabled:opacity-60 dark:bg-cyan-500 dark:text-zinc-950 dark:hover:bg-cyan-400"
            >
              {loading ? "Sending…" : "Send reset link"}
            </button>
          </form>
        )}

        <Link
          to="/login"
          className="mt-5 block text-center text-[11px] uppercase tracking-wide text-zinc-500 hover:underline dark:text-zinc-400"
        >
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
