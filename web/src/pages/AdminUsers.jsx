import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { adminApi } from "../lib/api.js";
import { auth } from "../lib/auth.js";
import ThemeToggle from "../components/ThemeToggle.jsx";

export default function AdminUsers() {
  const navigate = useNavigate();
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [newKey, setNewKey] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const selfId = auth.getUser()?.id;

  async function load() {
    try {
      const all = (await adminApi.listUsers()).filter((u) => u.id !== selfId);
      const keys = await Promise.all(all.map((u) => adminApi.getUserApiKeys(u.id)));
      setUsers(all.map((u, i) => ({ ...u, apiKeyStatus: latestKeyStatus(keys[i]) })));
    } catch (e) {
      setError(String(e.message || e));
    }
  }
  useEffect(() => { load(); }, []);

  function latestKeyStatus(keys) {
    if (!keys.length) return "none";
    return keys[keys.length - 1].status;
  }

  async function handleBlockToggle(u) {
    await (u.status === "blocked" ? adminApi.unblockUser(u.id) : adminApi.blockUser(u.id));
    load();
  }

  async function handleDelete(u) {
    if (!confirm(`Delete user "${u.email}"? This cannot be undone.`)) return;
    await adminApi.deleteUser(u.id);
    load();
  }

  async function handleGenerateKey(u) {
    const key = await adminApi.generateApiKey(u.id);
    setNewKey(key.raw_key);
    load();
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-6 dark:bg-zinc-950">
      <div className="mx-auto max-w-4xl">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <button onClick={() => navigate("/")} className="text-[12px] text-zinc-500 hover:text-zinc-800 dark:text-zinc-500 dark:hover:text-zinc-200">
              ← Back to dashboard
            </button>
            <h1 className="flex items-center gap-2 font-display text-[17px] font-semibold text-zinc-900 dark:text-zinc-100">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 dark:bg-cyan-400" />
              User Management
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCreate(true)}
              className="rounded bg-zinc-900 px-3 py-1.5 text-[12px] font-medium text-white transition hover:bg-zinc-800 dark:bg-cyan-500 dark:text-zinc-950 dark:hover:bg-cyan-400"
            >
              + Create user
            </button>
            <ThemeToggle />
          </div>
        </div>

        {error && <p className="mb-3 text-[12px] text-red-600 dark:text-red-400">{error}</p>}

        {newKey && (
          <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-[12px] dark:border-amber-500/30 dark:bg-amber-500/10">
            <p className="mb-1 font-medium text-amber-900 dark:text-amber-300">API key generated — save it now, it won't be shown again:</p>
            <code className="break-all text-amber-800 dark:text-amber-400">{newKey}</code>
            <button onClick={() => setNewKey(null)} className="ml-3 text-amber-700 underline dark:text-amber-400">dismiss</button>
          </div>
        )}

        <div className="overflow-hidden rounded border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <table className="w-full text-left text-[12px]">
            <thead className="border-b border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950/60 dark:text-zinc-500">
              <tr>
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Email</th>
                <th className="px-3 py-2 font-medium">Role</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">API Key</th>
                <th className="px-3 py-2 font-medium">Last login</th>
                <th className="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(users ?? []).map((u) => (
                <tr key={u.id} className="border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50 dark:border-zinc-800/60 dark:hover:bg-zinc-950/40">
                  <td className="px-3 py-2 text-zinc-800 dark:text-zinc-200">{u.name}</td>
                  <td className="px-3 py-2 text-zinc-800 dark:text-zinc-200">{u.email}</td>
                  <td className="px-3 py-2 text-zinc-600 dark:text-zinc-400">{u.role}</td>
                  <td className="px-3 py-2">
                    <span className={u.status === "blocked" ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}>
                      {u.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={
                      u.apiKeyStatus === "active" ? "text-emerald-600 dark:text-emerald-400"
                      : u.apiKeyStatus === "none" ? "text-zinc-400 dark:text-zinc-600"
                      : "text-red-600 dark:text-red-400"
                    }>
                      {u.apiKeyStatus ?? "…"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-zinc-500 dark:text-zinc-500">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "never"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1.5">
                      <button onClick={() => handleBlockToggle(u)}
                        className="rounded border border-zinc-300 px-2 py-1 transition hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
                        {u.status === "blocked" ? "Unblock" : "Block"}
                      </button>
                      <button onClick={() => handleGenerateKey(u)}
                        className="rounded border border-zinc-300 px-2 py-1 transition hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
                        Gen API key
                      </button>
                      <button onClick={() => handleDelete(u)}
                        className="rounded border border-red-300 px-2 py-1 text-red-600 transition hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10">
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users && users.length === 0 && (
            <p className="p-4 text-center text-[12px] text-zinc-500 dark:text-zinc-500">No users yet.</p>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateUserModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />
      )}
    </div>
  );
}

function CreateUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "user" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await adminApi.createUser(form);
      onCreated();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 grid place-items-center bg-black/30 backdrop-blur-sm dark:bg-black/60">
      <form onSubmit={submit} className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-5 shadow-lg dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-[0_0_40px_-10px_rgba(34,211,238,0.2)]">
        <h2 className="mb-3 text-[14px] font-semibold text-zinc-900 dark:text-zinc-100">Create user</h2>

        <input required placeholder="Name" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="mb-2 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-cyan-500" />
        <input required type="email" placeholder="Email" value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="mb-2 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-cyan-500" />
        <input required type="text" placeholder="Temporary password" value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          className="mb-2 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-cyan-500" />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
          className="mb-3 w-full rounded border border-zinc-300 px-2.5 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:focus:border-cyan-500">
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>

        {error && <p className="mb-2 text-[12px] text-red-600 dark:text-red-400">{error}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose}
            className="rounded border border-zinc-300 px-3 py-1.5 text-[12px] transition hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
            Cancel
          </button>
          <button type="submit" disabled={busy}
            className="rounded bg-zinc-900 px-3 py-1.5 text-[12px] font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50 dark:bg-cyan-500 dark:text-zinc-950 dark:hover:bg-cyan-400">
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
