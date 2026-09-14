// frontend-v2/src/routes/Dashboard.jsx
import { Link, useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Scale, LogOut, FileText, Route } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

import heroBg from "../assets/hero.jpg";

const EASE = [0.22, 1, 0.36, 1];

/* -------------------------------------------------------------------------- */
/*  Parcours — 2 étapes                                                       */
/* -------------------------------------------------------------------------- */
const STEPS = [
  {
    step: "1",
    to: "/features/contract",
    title: "Votre contrat",
    desc: "Importez un document. Dalil le lit pour vous.",
    icon: FileText,
    tag: "Analyse",
  },
  {
    step: "2",
    to: "/features/workflow",
    title: "Vos étapes",
    desc: "Suivez la procédure, sans rien oublier.",
    icon: Route,
    tag: "Procédure",
  },
];

export default function Dashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      if (typeof logout === "function") await logout();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      navigate("/", { replace: true });
    }
  };

  return (
    <main className="relative flex min-h-screen w-full flex-col overflow-hidden font-['Inter',system-ui,sans-serif] text-[#F7F3EA] antialiased">
      <div className="absolute inset-0">
        <img src={heroBg} alt="" aria-hidden className="h-full w-full object-cover" />
      </div>

      <div className="absolute inset-0 bg-[#050B16]/25" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#050B16]/45 via-[#050B16]/10 to-[#050B16]/65" />

      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 opacity-[0.10] [background-image:linear-gradient(to_right,rgba(247,243,234,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(247,243,234,0.08)_1px,transparent_1px)] [background-size:56px_56px] [mask-image:radial-gradient(80%_60%_at_50%_40%,black,transparent_25%)]" />
        <motion.div
          aria-hidden
          animate={{ x: [0, 30, -20, 0], y: [0, -20, 20, 0] }}
          transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -left-40 -top-52 h-[520px] w-[520px] rounded-full bg-[#E8C766]/[0.12] blur-[160px]"
        />
        <motion.div
          aria-hidden
          animate={{ x: [0, -40, 20, 0], y: [0, 20, -20, 0] }}
          transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -bottom-56 -right-44 h-[520px] w-[520px] rounded-full bg-[#F7F3EA]/[0.08] blur-[160px]"
        />
      </div>

      <motion.header
        initial={{ y: -40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: EASE, delay: 0.05 }}
        className="relative z-20"
      >
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#E8C766]/40 bg-[#E8C766]/15 backdrop-blur-md">
              <Scale size={16} className="text-[#E8C766]" />
            </div>
            <span className="text-base font-semibold tracking-tight text-[#F7F3EA] drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)]">
              Dalil
            </span>
          </Link>

          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 rounded-full border border-[#F7F3EA]/35 bg-[#050B16]/40 px-5 py-2 text-sm font-semibold text-[#F7F3EA] backdrop-blur-md transition-all duration-300 hover:border-[#E8C766]/60 hover:bg-[#E8C766]/15"
            aria-label="Se déconnecter"
          >
            <LogOut size={14} />
            <span className="hidden sm:inline">Quitter</span>
          </button>
        </div>
      </motion.header>

      <section className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center px-6 pb-16 pt-6 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: EASE, delay: 0.1 }}
          className="text-center"
        >
          <h1 className="text-3xl font-bold leading-tight tracking-[-0.02em] text-white drop-shadow-[0_4px_30px_rgba(0,0,0,0.6)] sm:text-4xl lg:text-5xl">
            Que voulez-vous faire ?
          </h1>
          <p className="mx-auto mt-4 max-w-md text-[15px] font-medium text-[#F7F3EA]/85 drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)]">
            Choisissez une carte pour commencer.
          </p>
        </motion.div>

        {/* 2 cartes, centrées */}
        <div className="mx-auto mt-12 grid w-full max-w-3xl flex-1 grid-cols-1 gap-6 md:grid-cols-2 lg:min-h-[360px]">
          {STEPS.map((s, i) => (
            <StepCard key={s.to} step={s} delay={0.2 + i * 0.12} />
          ))}
        </div>
      </section>

      <motion.footer
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: EASE, delay: 0.7 }}
        className="relative z-10 border-t border-[#F7F3EA]/15 bg-[#050B16]/40 backdrop-blur-md"
      >
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 py-5 sm:flex-row lg:px-10">
          <p className="text-[12px] font-medium text-[#F7F3EA]/70">
            © {new Date().getFullYear()} Dalil
          </p>
          <div className="flex items-center gap-6">
            <a href="#" className="text-[12px] font-medium text-[#F7F3EA]/60 transition-colors hover:text-[#E8C766]">
              Aide
            </a>
            <a href="#" className="text-[12px] font-medium text-[#F7F3EA]/60 transition-colors hover:text-[#E8C766]">
              Contact
            </a>
          </div>
        </div>
      </motion.footer>
    </main>
  );
}

function StepCard({ step, delay = 0 }) {
  const reduced = useReducedMotion();
  const { to, title, desc, icon: Icon, tag, step: number } = step;

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: EASE, delay }}
      whileHover={reduced ? undefined : { y: -10 }}
      whileTap={reduced ? undefined : { scale: 0.98 }}
      className="group relative h-full min-h-[320px]"
    >
      <Link
        to={to}
        className="relative flex h-full flex-col items-center justify-between overflow-hidden rounded-3xl border border-[#F7F3EA]/25 bg-[#050B16]/50 p-8 text-center backdrop-blur-xl transition-colors duration-300 hover:border-[#E8C766]/60 hover:bg-[#050B16]/65"
        style={{
          boxShadow:
            "0 10px 30px -10px rgba(0,0,0,0.6), inset 0 1px 0 rgba(247,243,234,0.10)",
        }}
      >
        <div className="pointer-events-none absolute inset-0 rounded-3xl bg-gradient-to-br from-[#F7F3EA]/[0.08] via-transparent to-transparent" />
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[45%] rounded-b-3xl bg-gradient-to-t from-[#E8C766]/[0.10] to-transparent" />

        <span className="relative rounded-full border border-[#F7F3EA]/20 bg-[#F7F3EA]/10 px-3 py-1 font-mono text-[9px] font-semibold uppercase tracking-[0.22em] text-[#F7F3EA]/80 backdrop-blur-md">
          {tag}
        </span>

        <div className="relative flex flex-1 flex-col items-center justify-center">
          <div className="relative">
            <div className="absolute inset-0 -z-10 rounded-full bg-[#E8C766]/25 blur-2xl transition-opacity duration-500 group-hover:opacity-100 opacity-70" />
            <span className="grid h-24 w-24 place-items-center rounded-full border-2 border-[#E8C766]/40 bg-[#050B16]/60 text-[#E8C766] backdrop-blur-md transition-all duration-300 group-hover:border-[#E8C766]/80 group-hover:scale-105 group-hover:shadow-[0_0_40px_rgba(232,199,102,0.5)]">
              <Icon size={38} strokeWidth={1.8} />
            </span>
            <span className="absolute -right-2 -top-2 grid h-8 w-8 place-items-center rounded-full border border-[#E8C766]/50 bg-[#050B16] font-mono text-sm font-bold text-[#E8C766]">
              {number}
            </span>
          </div>

          <h3 className="mt-6 text-2xl font-bold tracking-tight text-[#F7F3EA] drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)]">
            {title}
          </h3>
          <p className="mt-2 max-w-[220px] text-[13.5px] font-medium leading-relaxed text-[#F7F3EA]/80">
            {desc}
          </p>
        </div>

        <span className="relative mt-6 inline-flex items-center gap-2 rounded-full border border-[#E8C766]/40 bg-[#E8C766]/10 px-5 py-2 text-[12.5px] font-bold tracking-wide text-[#E8C766] transition-all duration-300 group-hover:border-[#E8C766]/70 group-hover:bg-[#E8C766]/20 group-hover:gap-3">
          Ouvrir
          <ArrowRight size={14} className="transition-transform duration-300 group-hover:translate-x-1" />
        </span>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[2px] origin-left scale-x-0 bg-gradient-to-r from-[#E8C766] via-[#FFF3C4] to-transparent transition-transform duration-500 group-hover:scale-x-100" />
      </Link>
    </motion.div>
  );
}