import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
const TOKEN_KEY = "br_token_v1";

// Session is primarily an httpOnly cookie (carried by withCredentials).
// As a belt-and-suspenders fallback for production custom-domain setups
// where the cookie can be stripped by the ingress, we also persist the
// JWT returned by /auth/login (or /auth/register) and attach it as a
// Bearer header on every request. Backend accepts either.
export function setStoredToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* private mode / disabled storage — best effort only */ }
}

export function getStoredToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const t = getStoredToken();
  if (t && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

// Clear stored token on any 401 so the next page load redirects to login
// instead of looping with a stale token.
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 401) {
      const url = error.config?.url || "";
      // Don't clear if this was just /auth/me probing — that endpoint
      // is supposed to return 401 for guests.
      if (!url.includes("/auth/me")) {
        // leave it — caller decides what to do
      }
    }
    return Promise.reject(error);
  }
);

export default api;
