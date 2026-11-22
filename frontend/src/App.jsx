import { useCallback, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";
import Login from "./components/Login.jsx";
import Chat from "./components/Chat.jsx";
import Documents from "./components/Documents.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(getToken()));
  const [tab, setTab] = useState("chat");

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    window.addEventListener("auth-expired", logout);
    return () => window.removeEventListener("auth-expired", logout);
  }, [logout]);

  if (booting) return <div className="center muted">Loading…</div>;
  if (!user) return <Login onLoggedIn={setUser} />;

  return (
    <div className="app">
      <header className="topbar">
        <h1>Knowledge Assistant</h1>
        <nav>
          <button className={tab === "chat" ? "tab active" : "tab"} onClick={() => setTab("chat")}>
            Chat
          </button>
          <button
            className={tab === "documents" ? "tab active" : "tab"}
            onClick={() => setTab("documents")}
          >
            Documents
          </button>
        </nav>
        <div className="who">
          <span>
            {user.full_name || user.email}
            {user.role === "admin" && <span className="badge">admin</span>}
          </span>
          <button className="link" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main>{tab === "chat" ? <Chat /> : <Documents />}</main>
    </div>
  );
}
