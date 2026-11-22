import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

function Sources({ citations }) {
  if (!citations?.length) return null;
  return (
    <details className="sources">
      <summary>
        {citations.length} source{citations.length > 1 ? "s" : ""}
      </summary>
      <ul>
        {citations.map((c) => (
          <li key={c.n}>
            <strong>
              [{c.n}] {c.filename}
              {c.page ? `, p.${c.page}` : ""}
            </strong>
            <div className="small muted">{c.snippet}</div>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default function Chat() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  const loadConversations = useCallback(
    () => api.listConversations().then(setConversations).catch(() => {}),
    []
  );

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function open(id) {
    setActiveId(id);
    setError("");
    setMessages(await api.getMessages(id));
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setError("");
  }

  async function remove(id) {
    await api.deleteConversation(id);
    if (id === activeId) newChat();
    loadConversations();
  }

  async function send(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setError("");
    setBusy(true);
    setMessages((m) => [...m, { id: `u${Date.now()}`, role: "user", content: question }]);
    try {
      const res = await api.chat(question, activeId);
      setActiveId(res.conversation_id);
      setMessages((m) => [
        ...m,
        { id: `a${Date.now()}`, role: "assistant", content: res.answer, citations: res.citations },
      ]);
      loadConversations();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-layout">
      <aside className="history">
        <button className="primary" onClick={newChat}>
          + New chat
        </button>
        <ul>
          {conversations.map((c) => (
            <li key={c.id} className={c.id === activeId ? "active" : ""}>
              <button className="convo" onClick={() => open(c.id)} title={c.title}>
                {c.title}
              </button>
              <button className="link danger" onClick={() => remove(c.id)} aria-label="Delete conversation">
                ×
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="thread">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty">
              <h2>Ask anything about your documents</h2>
              <p className="muted">Answers are grounded in the files you and your colleagues uploaded, with sources.</p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`bubble ${m.role}`}>
              <div className="text">{m.content}</div>
              {m.role === "assistant" && <Sources citations={m.citations} />}
            </div>
          ))}
          {busy && <div className="bubble assistant muted">Searching the knowledge base…</div>}
          {error && <div className="error">{error}</div>}
          <div ref={bottomRef} />
        </div>
        <form className="composer" onSubmit={send}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            maxLength={4000}
            autoFocus
          />
          <button className="primary" disabled={busy || !input.trim()}>
            Send
          </button>
        </form>
      </section>
    </div>
  );
}
