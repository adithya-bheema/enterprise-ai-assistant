const BASE = import.meta.env.VITE_API_URL || "/api";
const TOKEN_KEY = "kb_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) =>
  t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);

async function request(path, { method = "GET", json, form, body } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form; // FormData or URLSearchParams: the browser sets the content type
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body });
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) window.dispatchEvent(new Event("auth-expired"));
    const detail = data?.detail;
    throw new Error(
      typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : `Request failed (${res.status})`
    );
  }
  return data;
}

export const api = {
  async login(email, password) {
    const form = new URLSearchParams({ username: email, password });
    const { access_token } = await request("/auth/login", { method: "POST", form });
    setToken(access_token);
  },
  register: (email, password, full_name) =>
    request("/auth/register", { method: "POST", json: { email, password, full_name } }),
  me: () => request("/auth/me"),

  listDocuments: () => request("/documents"),
  uploadDocument(file, visibility) {
    const form = new FormData();
    form.append("file", file);
    form.append("visibility", visibility);
    return request("/documents", { method: "POST", form });
  },
  deleteDocument: (id) => request(`/documents/${id}`, { method: "DELETE" }),

  chat: (question, conversation_id) =>
    request("/chat", { method: "POST", json: { question, conversation_id } }),
  listConversations: () => request("/conversations"),
  getMessages: (id) => request(`/conversations/${id}/messages`),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: "DELETE" }),
};
