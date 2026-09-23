const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  getUser: () => JSON.parse(localStorage.getItem(USER_KEY) ?? "null"),
  setUser: (user) => localStorage.setItem(USER_KEY, JSON.stringify(user)),
  isAdmin: () => auth.getUser()?.role === "admin",
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  isAuthenticated: () => !!localStorage.getItem(TOKEN_KEY),
};
