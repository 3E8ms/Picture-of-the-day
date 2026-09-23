import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    display_name: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm({ ...form, [key]: e.target.value });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        display_name: form.display_name.trim() || form.username.trim(),
      });
      navigate("/");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Couldn't create your account.";
      setError(Array.isArray(msg) ? msg.map((m) => m.msg).join(" ") : msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1>📷 Picture of the Day</h1>
        <p className="muted">One photo a day keeps the boredom away.</p>
        <input
          placeholder="Username (letters, numbers, _ .)"
          value={form.username}
          onChange={set("username")}
          minLength={3}
          maxLength={30}
          required
        />
        <input
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={set("email")}
          required
        />
        <input
          placeholder="Display name"
          value={form.display_name}
          onChange={set("display_name")}
          maxLength={80}
        />
        <input
          type="password"
          placeholder="Password (min 8 characters)"
          value={form.password}
          onChange={set("password")}
          minLength={8}
          autoComplete="new-password"
          required
        />
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Sign up"}
        </button>
        <p className="muted">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
