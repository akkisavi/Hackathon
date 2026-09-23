const KEY = "theme";

function apply(t) {
  document.documentElement.classList.toggle("dark", t === "dark");
  window.dispatchEvent(new CustomEvent("themechange", { detail: t }));
}

export const theme = {
  get: () =>
    localStorage.getItem(KEY) ??
    (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  set(t) {
    localStorage.setItem(KEY, t);
    apply(t);
  },
  init() {
    apply(theme.get());
  },
  toggle() {
    const next = theme.get() === "dark" ? "light" : "dark";
    theme.set(next);
    return next;
  },
};
