import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [visibility, setVisibility] = useState("org");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  const refresh = useCallback(() => api.listDocuments().then(setDocs).catch((e) => setError(e.message)), []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any document is still being embedded.
  const processing = docs.some((d) => d.status === "processing");
  useEffect(() => {
    if (!processing) return;
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [processing, refresh]);

  async function upload(e) {
    e.preventDefault();
    const files = Array.from(fileRef.current?.files || []);
    if (!files.length) return;
    setError("");
    setUploading(true);
    try {
      for (const f of files) await api.uploadDocument(f, visibility);
      fileRef.current.value = "";
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function remove(doc) {
    if (!window.confirm(`Delete "${doc.filename}" and its indexed content?`)) return;
    try {
      await api.deleteDocument(doc.id);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <form className="card upload" onSubmit={upload}>
        <h2>Add documents</h2>
        <p className="muted">PDF, Word (.docx), Markdown or text files.</p>
        <div className="row">
          <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.txt,.md" />
          <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
            <option value="org">Visible to everyone</option>
            <option value="private">Only me</option>
          </select>
          <button className="primary" disabled={uploading}>
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </form>

      <div className="card">
        <h2>Library ({docs.length})</h2>
        {docs.length === 0 ? (
          <p className="muted">No documents yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Access</th>
                <th>Status</th>
                <th>Chunks</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.filename}</td>
                  <td>{d.visibility === "org" ? "Everyone" : "Private"}</td>
                  <td>
                    <span className={`status ${d.status}`} title={d.error || ""}>
                      {d.status}
                    </span>
                    {d.status === "failed" && d.error && <div className="small error">{d.error}</div>}
                  </td>
                  <td>{d.chunk_count}</td>
                  <td>
                    <button className="link danger" onClick={() => remove(d)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
