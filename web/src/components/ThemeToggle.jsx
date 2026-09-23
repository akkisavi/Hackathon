import { useState } from "react";
import { theme } from "../lib/theme.js";

export default function ThemeToggle({ className = "" }) {
  const [current, setCurrent] = useState(theme.get());

  return (
    <button
      type="button"
      onClick={() => setCurrent(theme.toggle())}
      title={current === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className={`grid h-7 w-7 shrink-0 place-items-center rounded border border-zinc-300 text-zinc-500 transition hover:border-zinc-400 hover:text-zinc-800 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-500 dark:hover:text-zinc-100 ${className}`}
    >
      {current === "dark" ? (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
          <path d="M10 2a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm0 14a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1ZM3 9a1 1 0 1 0 0 2h1a1 1 0 1 0 0-2H3Zm13 0a1 1 0 1 0 0 2h1a1 1 0 1 0 0-2h-1ZM4.93 4.93a1 1 0 0 1 1.41 0l.71.71a1 1 0 1 1-1.41 1.41l-.71-.71a1 1 0 0 1 0-1.41Zm8.02 8.02a1 1 0 0 1 1.41 0l.71.71a1 1 0 1 1-1.41 1.41l-.71-.71a1 1 0 0 1 0-1.41ZM15.07 4.93a1 1 0 0 1 0 1.41l-.71.71a1 1 0 1 1-1.41-1.41l.71-.71a1 1 0 0 1 1.41 0ZM7.05 12.95a1 1 0 0 1 0 1.41l-.71.71a1 1 0 1 1-1.41-1.41l.71-.71a1 1 0 0 1 1.41 0ZM10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" />
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
          <path d="M17.293 13.293A8 8 0 0 1 6.707 2.707a8.001 8.001 0 1 0 10.586 10.586Z" />
        </svg>
      )}
    </button>
  );
}
