// frontend-v2/src/components/AuthModal.jsx
import { useEffect, useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { X, User, Mail, Lock, ArrowRight, Scale, Gavel, Sparkles, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const EASE = [0.22, 1, 0.36, 1];

export default function AuthModal({ open, onClose, mode = "login" }) {
  const { login, register, loading } = useAuth();
  const navigate = useNavigate();
  const reduced = useReducedMotion();

  const isOfficer = mode === "officer";
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

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

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
      if (s === 401 || s === 400) setError("Identifiants ou données d'inscription invalides.");
      else setError("Une erreur est survenue. Veuillez réessayer.");
    }
  };

  const title = isOfficer
    ? "Accès agent"
    : tab === "signup"
    ? "Créer votre compte"
    : "Bon retour";

  const subtitle = isOfficer
    ? "Réservé aux agents de justice et médiateurs accrédités."
    : tab === "signup"
    ? "La justice commerciale, sans papier — dès maintenant."
    : "Connectez-vous pour continuer votre dossier.";

  const HeaderIcon = isOfficer ? Gavel : tab === "signup" ? Sparkles : Scale;
  const submitLabel = isOfficer
    ? "Se connecter en tant qu'agent"
    : tab === "signup"
    ? "Créer un compte"
    : "Se connecter";

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="auth-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25, ease: EASE }}
          onClick={onClose}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          style={{
            backgroundColor: "rgba(5,11,22,0.55)",
            backdropFilter: "blur(10px)",
            WebkitBackdropFilter: "blur(10px)",
          }}
        >
          <motion.div
            key="auth-card"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.35, ease: EASE }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-md overflow-hidden rounded-2xl border border-[#050B16]/10 bg-[#F7F3EA] p-7 text-[#050B16] shadow-[0_30px_80px_-20px_rgba(0,0,0,0.6)] sm:p-8"
          >
            <div className="pointer-events-none absolute -right-24 -top-24 h-[220px] w-[220px] rounded-full bg-[#E8C766]/25 blur-[80px]" />
            <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[45%] rounded-b-2xl bg-gradient-to-t from-[#E8C766]/10 to-transparent" />

            <button
              onClick={onClose}
              aria-label="Fermer"
              className="absolute right-4 top-4 z-10 grid h-9 w-9 place-items-center rounded-full border border-[#050B16]/10 bg-[#050B16]/[0.04] text-[#050B16]/60 transition-all duration-300 hover:border-[#050B16]/20 hover:bg-[#050B16]/[0.08] hover:text-[#050B16]"
            >
              <X size={15} />
            </button>

            <div className="relative">
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.4, ease: EASE, delay: 0.05 }}
                className="grid h-12 w-12 place-items-center rounded-xl border border-[#050B16]/10 bg-[#050B16] text-[#E8C766] shadow-[0_10px_30px_-10px_rgba(5,11,22,0.5)]"
              >
                <HeaderIcon size={20} />
              </motion.div>

              <motion.h2
                key={`title-${mode}-${tab}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: EASE, delay: 0.08 }}
                className="mt-5 text-2xl font-bold tracking-tight text-[#050B16]"
              >
                {title}
              </motion.h2>

              <motion.p
                key={`sub-${mode}-${tab}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: EASE, delay: 0.12 }}
                className="mt-1.5 text-[13.5px] font-medium text-[#050B16]/65"
              >
                {subtitle}
              </motion.p>
            </div>

            <form onSubmit={onSubmit} className="relative mt-7 space-y-4">
              <Field
                icon={<User size={15} />}
                name="username"
                type="text"
                placeholder="Nom d'utilisateur"
                value={form.username}
                onChange={onChange}
                autoComplete="username"
                autoFocus
                required
              />

              {tab === "signup" && !isOfficer && (
                <Field
                  icon={<Mail size={15} />}
                  name="email"
                  type="email"
                  placeholder="Adresse e-mail"
                  value={form.email}
                  onChange={onChange}
                  autoComplete="email"
                />
              )}

              <Field
                icon={<Lock size={15} />}
                name="password"
                type="password"
                placeholder="Mot de passe"
                value={form.password}
                onChange={onChange}
                autoComplete={tab === "signup" ? "new-password" : "current-password"}
                minLength={tab === "signup" ? 6 : undefined}
                required
              />

              {isOfficer && (
                <div className="flex items-start gap-2 rounded-xl border border-[#050B16]/10 bg-[#050B16]/[0.04] px-3.5 py-2.5 text-[11.5px] font-medium leading-relaxed text-[#050B16]/70">
                  <ShieldCheck size={13} className="mt-[2px] shrink-0 text-[#050B16]" />
                  <span>
                    Les comptes agents sont créés par l'administration de votre
                    tribunal. Utilisez les identifiants qui vous ont été remis.
                  </span>
                </div>
              )}

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-red-500/25 bg-red-500/10 px-3.5 py-2.5 text-[12.5px] font-medium text-red-700"
                >
                  {error}
                </motion.div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="group relative mt-2 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#050B16] px-6 py-3 text-sm font-bold tracking-wide text-[#F7F3EA] shadow-[0_10px_30px_-10px_rgba(5,11,22,0.6)] transition-all duration-300 hover:bg-[#0B1526] hover:shadow-[0_14px_40px_-10px_rgba(5,11,22,0.8)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <motion.span
                      animate={reduced ? undefined : { rotate: 360 }}
                      transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
                      className="inline-block h-3.5 w-3.5 rounded-full border-2 border-[#F7F3EA]/30 border-t-[#E8C766]"
                    />
                    Veuillez patienter…
                  </>
                ) : (
                  <>
                    {submitLabel}
                    <ArrowRight
                      size={15}
                      className="transition-transform duration-300 group-hover:translate-x-1"
                    />
                  </>
                )}
              </button>
            </form>

            {mode !== "officer" && (
              <div className="relative mt-6 flex items-center justify-center gap-1.5 text-[13px] font-medium text-[#050B16]/60">
                <span>
                  {tab === "login"
                    ? "Nouveau sur Dalil ?"
                    : "Vous avez déjà un compte ?"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setError("");
                    setTab(tab === "login" ? "signup" : "login");
                  }}
                  className="font-bold text-[#050B16] underline-offset-4 transition-colors hover:text-[#8a6f1f] hover:underline"
                >
                  {tab === "login" ? "Créer un compte" : "Se connecter"}
                </button>
              </div>
            )}

            {tab === "login" && !isOfficer && (
              <div className="relative mt-3 text-center">
                <a
                  href="#"
                  className="text-[12px] font-medium text-[#050B16]/50 underline-offset-4 transition-colors hover:text-[#050B16] hover:underline"
                >
                  Mot de passe oublié ?
                </a>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* -------------------------------------------------------------------------- */
/*  Champ                                                                     */
/* -------------------------------------------------------------------------- */
function Field({
  icon,
  name,
  type,
  placeholder,
  value,
  onChange,
  autoComplete,
  autoFocus,
  minLength,
  required,
}) {
  return (
    <div className="group relative">
      <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#050B16]/40 transition-colors group-focus-within:text-[#050B16]">
        {icon}
      </span>
      <input
        name={name}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        minLength={minLength}
        required={required}
        className="w-full rounded-xl border border-[#050B16]/15 bg-white py-3 pl-10 pr-3.5 text-sm font-medium text-[#050B16] outline-none transition-all duration-300 placeholder:text-[#050B16]/35 focus:border-[#050B16]/40 focus:bg-white focus:shadow-[0_0_0_4px_rgba(232,199,102,0.25)]"
      />
    </div>
  );
}