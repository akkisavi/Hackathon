import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import ThemeToggle from "../components/ThemeToggle.jsx";

export default function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [apiKeys, setApiKeys] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.me().then(setUser).catch((e) => setError(String(e.message || e)));
    api.myApiKeys().then(setApiKeys).catch(() => {});
  }, []);

  const latestKey = apiKeys?.length ? apiKeys[apiKeys.length - 1] : null;

  return (
    <div className="min-h-screen bg-zinc-50 p-6 dark:bg-zinc-950">
      <div className="mx-auto max-w-md">
        <div className="mb-2 flex items-center justify-between">
          <button onClick={() => navigate("/")} className="text-[12px] text-zinc-500 hover:text-zinc-800 dark:text-zinc-500 dark:hover:text-zinc-200">
            ← Back to dashboard
          </button>
          <ThemeToggle />
        </div>
        <h1 className="mb-4 flex items-center gap-2 font-display text-[17px] font-semibold text-zinc-900 dark:text-zinc-100">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 dark:bg-cyan-400" />
          Profile
        </h1>

        {error && <p className="mb-3 text-[12px] text-red-600 dark:text-red-400">{error}</p>}

        <div className="mb-4 rounded-lg border border-zinc-200 bg-white p-4 text-[13px] shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <Row label="Name" value={user?.name ?? "…"} />
          <Row label="Email" value={user?.email ?? "…"} />
          <Row label="Role" value={user?.role ?? "…"} />
          <Row
            label="API key"
            value={
              !apiKeys ? "…"
              : latestKey ? `${latestKey.status}${latestKey.expires_at ? ` (expires ${new Date(latestKey.expires_at).toLocaleDateString()})` : ""}`
              : "none issued — ask an admin"
            }
          />
        </div>

        <ChangePasswordForm />
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="mb-2 flex justify-between border-b border-zinc-100 pb-2 last:mb-0 last:border-0 last:pb-0 dark:border-zinc-800/60">
      <span className="text-zinc-500 dark:text-zinc-500">{label}</span>
      <span className="font-mono font-medium text-zinc-900 dark:text-zinc-100">{value}</span>
    </div>
  );
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(null); setSuccess(false);
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword });
      setSuccess(true);
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="mb-3 text-[13px] font-semibold text-zinc-900 dark:text-zinc-100">Reset password</h2>

      <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">Current password</label>
      <input type="password" required value={currentPassword}
        onChange={(e) => setCurrentPassword(e.target.value)}
        className="mb-2 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-cyan-500" />

      <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">New password</label>
      <input type="password" required value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        className="mb-2 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-cyan-500" />

      <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">Confirm new password</label>
      <input type="password" required value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        className="mb-3 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-cyan-500" />

      {error && <p className="mb-2 text-[12px] text-red-600 dark:text-red-400">{error}</p>}
      {success && <p className="mb-2 text-[12px] text-emerald-600 dark:text-emerald-400">Password changed.</p>}

      <button type="submit" disabled={busy}
        className="w-full rounded bg-zinc-900 px-3 py-1.5 text-[13px] font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50 dark:bg-cyan-500 dark:text-zinc-950 dark:hover:bg-cyan-400">
        {busy ? "Saving…" : "Change password"}
      </button>
    </form>
  );
}
