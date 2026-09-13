import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function AuthModal({ open, onClose, mode = "login" }) {
  const { login, register, loading } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState(mode === "signup" ? "signup" : "login");
  const [form, setForm] = useState({ username: "", password: "", email: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setTab(mode === "signup" ? "signup" : "login");
      setForm({ username: "", password: "", email: "" });
      setError("");
    }
  }, [open, mode]);

  if (!open) return null;

  const onChange = (e) =>
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      let u;
      if (tab === "signup") {
        u = await register(form.username, form.email, form.password);
      } else {
        u = await login(form.username, form.password);
      }
      onClose?.();
      if (u.role === "officer") navigate("/officer");
      else navigate("/dashboard");
    } catch (err) {
      const s = err?.response?.status;
      if (s === 401 || s === 400) setError("Invalid credentials or signup data.");
      else setError("Something went wrong. Try again.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="absolute top-3 right-3 text-slateDalil/60 hover:text-navy"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={20} />
        </button>

        <h2 className="text-2xl font-semibold text-navy mb-1">
          {tab === "signup" ? "Create your account" : "Welcome back"}
        </h2>

        {mode === "officer" && (
          <p className="text-xs text-gold-dark mb-3">
            Officers only. Credentials are provided by the court.
          </p>
        )}

        <form onSubmit={onSubmit} className="space-y-3 mt-4">
          <div>
            <label className="text-sm text-slateDalil/80">Username</label>
            <input
              name="username"
              className="input mt-1"
              value={form.username}
              onChange={onChange}
              required
              autoFocus
            />
          </div>

          {tab === "signup" && (
            <div>
              <label className="text-sm text-slateDalil/80">Email</label>
              <input
                type="email"
                name="email"
                className="input mt-1"
                value={form.email}
                onChange={onChange}
              />
            </div>
          )}

          <div>
            <label className="text-sm text-slateDalil/80">Password</label>
            <input
              type="password"
              name="password"
              className="input mt-1"
              value={form.password}
              onChange={onChange}
              required
              minLength={tab === "signup" ? 6 : undefined}
            />
          </div>

          {error && (
            <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
            {loading ? "Loading..." : tab === "signup" ? "Sign up" : "Log in"}
          </button>
        </form>

        {mode !== "officer" && (
          <button
            type="button"
            onClick={() => {
              setError("");
              setTab(tab === "login" ? "signup" : "login");
            }}
            className="text-sm text-navy hover:text-gold mt-4 w-full text-center"
          >
            {tab === "login"
              ? "No account? Create one"
              : "Already have an account? Log in"}
          </button>
        )}
      </div>
    </div>
  );
}