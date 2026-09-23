import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Post } from "../api/client";

const MAX_MB = 5;

export function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    setError("");
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setError("Please choose an image file.");
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`Image must be under ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("image", file);
      form.append("caption", caption);
      const res = await api.post<Post>("/posts", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate(`/p/${res.data.id}`);
    } catch {
      setError("Upload failed. Try a different image.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="upload-page">
      <h2>New Post</h2>
      <form onSubmit={submit} className="upload-form">
        <label className="upload-drop">
          {preview ? (
            <img src={preview} alt="Preview" className="upload-preview" />
          ) : (
            <span>📷 Click to choose a photo</span>
          )}
          <input
            type="file"
            accept="image/*"
            onChange={pick}
            hidden
          />
        </label>
        <textarea
          placeholder="Write a caption…"
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          maxLength={2000}
          rows={3}
        />
        {error && <p className="error">{error}</p>}
        <button
          className="btn btn-primary"
          type="submit"
          disabled={!file || busy}
        >
          {busy ? "Publishing…" : "Share"}
        </button>
      </form>
    </div>
  );
}
