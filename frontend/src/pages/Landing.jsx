// frontend-v2/src/routes/index.tsx

import { useRef, useState } from "react";
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useReducedMotion,
} from "framer-motion";
import {
  ArrowRight,
  FileText,
  Route,
  Gavel,
  Scale,
  Sparkles,
  Lock,
} from "lucide-react";

import AuthModal from "../components/AuthModal.jsx";
import heroBg from "../assets/hero.jpg";

const INK = "#050B16";
const CREAM = "#F7F3EA";
const GOLD = "#E8C766";

const EASE = [0.22, 1, 0.36, 1];

const riseIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

const stagger = (step = 0.08, delay = 0) => ({
  hidden: {},
  visible: { transition: { staggerChildren: step, delayChildren: delay } },
});

function ShiningText({ children }) {
  const reduced = useReducedMotion();
  if (reduced) return <span className="font-semibold text-[#E8C766]">{children}</span>;

  return (
    <motion.span
      className="inline-block font-semibold"
      animate={{ backgroundPosition: ["0% 0%", "100% 0%", "0% 0%"] }}
      transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
      style={{
        backgroundImage:
          "linear-gradient(90deg, #F7F3EA 0%, #E8C766 25%, #FFF3C4 50%, #E8C766 75%, #F7F3EA 100%)",
        backgroundSize: "300% 100%",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        backgroundClip: "text",
        textShadow: "0 0 40px rgba(232,199,102,0.35)",
      }}
    >
      {children}
    </motion.span>
  );
}

export default function Landing() {
  const [modal, setModal] = useState({ open: false, mode: "login" });

  const open = (mode) => setModal({ open: true, mode });
  const close = () => setModal((m) => ({ ...m, open: false }));

  return (
    <main
      className="relative h-screen w-full overflow-hidden font-['Inter',system-ui,sans-serif] text-[#F7F3EA] antialiased"
      style={{ backgroundColor: INK }}
    >
      <ScrollProgress />
      <Nav onOpen={open} />
      <Hero onOpen={open} />
      <Footer onOpen={open} />
      <AuthModal open={modal.open} mode={modal.mode} onClose={close} />
    </main>
  );
}

function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 140,
    damping: 24,
    restDelta: 0.001,
  });
  return (
    <motion.div
      aria-hidden
      style={{ scaleX }}
      className="fixed inset-x-0 top-0 z-50 h-[2px] origin-left bg-[#E8C766]/70"
    />
  );
}

function Nav({ onOpen }) {
  return (
    <motion.header
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: EASE, delay: 0.05 }}
      className="absolute inset-x-0 top-0 z-40"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
        <a href="#top" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#E8C766]/40 bg-[#E8C766]/15 backdrop-blur-md">
            <Scale size={16} className="text-[#E8C766]" />
          </div>
          <span className="text-base font-semibold tracking-tight text-[#F7F3EA]">
            Dalil
          </span>
        </a>

        <div className="hidden items-center gap-1 md:flex">
          <a href="#features" className="rounded-full px-4 py-2 text-sm font-medium text-[#F7F3EA]/80 transition hover:bg-[#F7F3EA]/10 hover:text-[#F7F3EA]">
            Fonctionnalités
          </a>
          <a href="#how" className="rounded-full px-4 py-2 text-sm font-medium text-[#F7F3EA]/80 transition hover:bg-[#F7F3EA]/10 hover:text-[#F7F3EA]">
            Fonctionnement
          </a>
          <a href="#about" className="rounded-full px-4 py-2 text-sm font-medium text-[#F7F3EA]/80 transition hover:bg-[#F7F3EA]/10 hover:text-[#F7F3EA]">
            À propos
          </a>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpen("login")}
            className="rounded-full border border-[#F7F3EA]/25 bg-[#F7F3EA]/10 px-5 py-2 text-sm font-medium text-[#F7F3EA] backdrop-blur-md transition hover:border-[#E8C766]/50 hover:bg-[#E8C766]/15"
          >
            Se connecter
          </button>
        </div>
      </div>
    </motion.header>
  );
}

function Hero({ onOpen }) {
  const reduced = useReducedMotion();
  const sectionRef = useRef(null);

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end start"],
  });
  const bgScale = useTransform(scrollYProgress, [0, 1], [1, 1.08]);
  const bgY = useTransform(scrollYProgress, [0, 1], ["0%", "6%"]);

  return (
    <section
      id="top"
      ref={sectionRef}
      className="relative flex h-screen w-full items-center justify-center overflow-hidden"
    >
      <motion.div
        style={reduced ? undefined : { scale: bgScale, y: bgY }}
        className="absolute inset-0"
      >
        <img src={heroBg} alt="" aria-hidden className="h-full w-full object-cover" />
      </motion.div>

      <div className="absolute inset-0 bg-[#050B16]/30" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#050B16]/55 via-[#050B16]/15 to-[#050B16]/75" />

      <GridOverlay />
      <Aurora />

      <div className="relative z-10 mx-auto flex w-full max-w-5xl flex-col items-center px-6 pt-24 pb-16 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger(0.08, 0.1)}>
          <motion.span
            variants={riseIn}
            className="inline-flex items-center gap-2 rounded-full border border-[#E8C766]/50 bg-[#050B16]/40 px-4 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.28em] text-[#E8C766] backdrop-blur-md"
          >
            <Sparkles size={11} />
            Justice commerciale pour les PME
          </motion.span>

          <motion.h1
            variants={riseIn}
            className="mt-6 text-[2.5rem] font-bold leading-[1.05] tracking-[-0.03em] text-white drop-shadow-[0_4px_30px_rgba(0,0,0,0.6)] sm:text-6xl lg:text-[4.25rem]"
          >
            <span className="sr-only">Maîtrisez vos contrats commerciaux, sans papier.</span>
            <span aria-hidden className="flex flex-wrap justify-center gap-x-[0.28em]">
              <span>Maîtrisez vos contrats commerciaux,</span>
              <ShiningText>sans papier.</ShiningText>
            </span>
          </motion.h1>

          <motion.p
            variants={riseIn}
            className="mx-auto mt-5 max-w-2xl text-base font-medium leading-relaxed text-[#F7F3EA] drop-shadow-[0_2px_12px_rgba(0,0,0,0.7)] sm:text-lg"
          >
            Dalil aide les PME à comprendre leurs contrats et à suivre la bonne
            procédure, étape par étape — sans paperasse ni jargon juridique.
          </motion.p>

          <motion.div
            variants={riseIn}
            className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <button
              onClick={() => onOpen("signup")}
              className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#E8C766] px-8 py-3.5 text-sm font-bold tracking-wide text-[#050B16] shadow-[0_10px_40px_-8px_rgba(232,199,102,0.8)] transition-all duration-300 hover:bg-[#F0D488] hover:shadow-[0_10px_50px_-8px_rgba(232,199,102,1)] sm:w-auto"
            >
              Commencer
              <ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => onOpen("login")}
              className="inline-flex w-full items-center justify-center rounded-full border border-[#F7F3EA]/40 bg-[#050B16]/40 px-8 py-3.5 text-sm font-semibold tracking-wide text-[#F7F3EA] backdrop-blur-md transition-all duration-300 hover:border-[#F7F3EA]/70 hover:bg-[#050B16]/60 sm:w-auto"
            >
              Se connecter
            </button>
          </motion.div>

          {/* 2 fonctionnalités */}
          <motion.div
            id="features"
            variants={riseIn}
            className="mx-auto mt-12 grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2"
          >
            <MiniCard
              icon={<FileText size={18} />}
              title="Compréhension du contrat"
              copy="Déposez un contrat (PDF ou photo) : le texte est extrait automatiquement, les clauses obligatoires sont vérifiées et les éléments manquants sont signalés."
              delay={0.1}
            />
            <MiniCard
              icon={<Route size={18} />}
              title="Accompagnement procédural"
              copy="Dalil vous guide pas à pas dans les démarches juridiques : quoi faire, dans quel ordre, et avant quelle échéance."
              delay={0.2}
            />
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

function MiniCard({ icon, title, copy, delay = 0 }) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE, delay }}
      whileHover={reduced ? undefined : { y: -6 }}
      className="group relative flex flex-col items-start overflow-hidden rounded-2xl border border-[#F7F3EA]/25 bg-[#050B16]/50 p-5 text-left backdrop-blur-xl transition-colors duration-300 hover:border-[#E8C766]/60 hover:bg-[#050B16]/65"
      style={{
        boxShadow:
          "0 10px 30px -10px rgba(0,0,0,0.6), inset 0 1px 0 rgba(247,243,234,0.10)",
      }}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-[#F7F3EA]/[0.08] via-transparent to-transparent" />
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[45%] rounded-b-2xl bg-gradient-to-t from-[#E8C766]/[0.08] to-transparent" />

      <span className="relative grid h-11 w-11 place-items-center rounded-xl border border-[#E8C766]/40 bg-[#E8C766]/15 text-[#E8C766] transition-all duration-300 group-hover:bg-[#E8C766]/25 group-hover:shadow-[0_0_25px_rgba(232,199,102,0.35)]">
        {icon}
      </span>

      <h3 className="relative mt-4 text-[15px] font-semibold tracking-tight text-[#F7F3EA]">
        {title}
      </h3>
      <p className="relative mt-1.5 text-[12.5px] font-normal leading-relaxed text-[#F7F3EA]/75">
        {copy}
      </p>
    </motion.div>
  );
}

function Footer({ onOpen }) {
  return (
    <motion.footer
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE, delay: 0.9 }}
      className="absolute inset-x-0 bottom-0 z-40"
    >
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-6 py-5 sm:flex-row lg:px-10">
        <p className="text-[12px] font-medium text-[#F7F3EA]/70 drop-shadow-[0_2px_10px_rgba(0,0,0,0.7)]">
          © {new Date().getFullYear()} Dalil — Justice commerciale pour les PME.
        </p>

        <button
          onClick={() => onOpen("officer")}
          className="group inline-flex items-center gap-2 rounded-full border border-[#E8C766]/45 bg-[#050B16]/50 px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-[#E8C766] backdrop-blur-md transition-all duration-300 hover:border-[#E8C766] hover:bg-[#E8C766] hover:text-[#050B16]"
        >
          <Lock size={11} />
          Agent / Médiateur
          <Gavel size={11} />
        </button>
      </div>
    </motion.footer>
  );
}

function GridOverlay() {
  const reduced = useReducedMotion();
  return (
    <motion.div
      aria-hidden
      animate={reduced ? undefined : { backgroundPositionY: ["0px", "56px"] }}
      transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
      className="pointer-events-none absolute inset-0 opacity-[0.10] [background-image:linear-gradient(to_right,rgba(247,243,234,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(247,243,234,0.08)_1px,transparent_1px)] [background-size:56px_56px] [mask-image:radial-gradient(80%_60%_at_50%_40%,black,transparent_25%)]"
    />
  );
}

function Aurora() {
  const reduced = useReducedMotion();
  return (
    <>
      <motion.div
        aria-hidden
        animate={reduced ? undefined : { x: [0, 20, -20, 0], y: [0, -30, 20, 0], scale: [1, 1.12, 0.96, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute -left-40 -top-52 h-[520px] w-[520px] rounded-full bg-[#E8C766]/[0.10] blur-[160px]"
      />
      <motion.div
        aria-hidden
        animate={reduced ? undefined : { x: [0, -50, 25, 0], y: [0, 25, -20, 0], scale: [1, 0.94, 1.1, 1] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute -bottom-56 -right-44 h-[520px] w-[520px] rounded-full bg-[#F7F3EA]/[0.06] blur-[160px]"
      />
    </>
  );
}