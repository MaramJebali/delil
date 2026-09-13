// frontend-v2/src/routes/features/WorkflowGuidance.jsx
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Send, Mic, MicOff, Volume2, Loader2,
  Scale, Store, Home, AlertCircle, Route,
} from "lucide-react";

import api from "../../api/axios";

const EASE = [0.22, 1, 0.36, 1];
const NAV_OFFSET = "h-[80px]";

const SCROLL_AREA =
  "min-h-0 flex-1 overflow-y-auto overscroll-contain " +
  "[scrollbar-width:thin] [scrollbar-color:rgba(5,11,22,0.18)_transparent] " +
  "[&::-webkit-scrollbar]:w-1.5 " +
  "[&::-webkit-scrollbar-track]:bg-transparent " +
  "[&::-webkit-scrollbar-thumb]:rounded-full " +
  "[&::-webkit-scrollbar-thumb]:bg-[#050B16]/15 " +
  "hover:[&::-webkit-scrollbar-thumb]:bg-[#050B16]/25";

/* -------------------------------------------------------------------------- */
/*  Streaming text                                                            */
/* -------------------------------------------------------------------------- */
function StreamingText({ text, onDone, speed = 22 }) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    setShown("");
    if (!text) return;
    let i = 0;
    let timeoutId;

    const tick = () => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) {
        onDone?.();
        return;
      }
      const lastChar = text[i - 1];
      const extra = /[.,;:!?]/.test(lastChar) ? 6 : 1;
      timeoutId = setTimeout(tick, speed * extra);
    };

    timeoutId = setTimeout(tick, speed);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  return <span className="whitespace-pre-wrap">{shown}</span>;
}

/* -------------------------------------------------------------------------- */
/*  Nav                                                                       */
/* -------------------------------------------------------------------------- */
function Nav() {
  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: EASE }}
      className="fixed inset-x-0 top-0 z-50"
    >
      <div className="mx-auto max-w-7xl px-4 pt-3 lg:px-6">
        <div className="flex h-16 items-center justify-between rounded-2xl border border-white/10 bg-[#050B16]/90 backdrop-blur-2xl shadow-[0_8px_40px_-12px_rgba(5,11,22,0.6)]">
          <div className="flex items-center gap-2.5 pl-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#E8C766]/50 bg-[#E8C766]/15">
              <Route size={16} className="text-[#E8C766]" />
            </div>
            <span className="text-[15px] font-semibold tracking-tight text-[#F7F3EA]">
              Accompagnement procédural
            </span>
          </div>

          <div className="pr-4">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium text-[#F7F3EA] backdrop-blur-md transition-all hover:border-[#E8C766]/50 hover:bg-[#E8C766]/15 hover:text-[#E8C766]"
            >
              <ArrowLeft size={14} /> Retour
            </Link>
          </div>
        </div>
      </div>
    </motion.header>
  );
}

/* -------------------------------------------------------------------------- */
/*  Footer                                                                    */
/* -------------------------------------------------------------------------- */
function Footer() {
  return (
    <motion.footer
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE, delay: 0.3 }}
      className="relative z-10 shrink-0 border-t border-[#050B16]/8 bg-[#FAF7F0]/60 backdrop-blur-md"
    >
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-6 py-3 sm:flex-row lg:px-10">
        <p className="text-[12px] font-medium text-[#050B16]/55">
          © {new Date().getFullYear()} Dalil — Justice commerciale pour les PME.
        </p>
        <div className="flex items-center gap-6">
          <a href="#" className="text-[12px] font-medium text-[#050B16]/55 transition-colors hover:text-[#050B16]">
            Aide
          </a>
          <a href="#" className="text-[12px] font-medium text-[#050B16]/55 transition-colors hover:text-[#050B16]">
            Contact
          </a>
        </div>
      </div>
    </motion.footer>
  );
}

/* -------------------------------------------------------------------------- */
/*  Cartes avocats — strip horizontal défilable                               */
/* -------------------------------------------------------------------------- */
function LawyerCards({ tool }) {
  const items = tool?.items || [];
  if (!items.length) return null;

  const region = tool.region_detected;

  return (
    <div className="mt-4 w-full">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[12px] font-medium uppercase tracking-wide text-[#050B16]/50">
          {region ? `Avocats — ${region}` : "Avocats recommandés"}
        </p>
        <p className="text-[11px] text-[#050B16]/40">
          {items.length} résultat{items.length > 1 ? "s" : ""}
        </p>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-3 -mx-1 px-1">
        {items.map((l) => (
          <div
            key={l.id}
            className="min-w-[280px] max-w-[280px] flex-shrink-0 rounded-2xl border border-[#050B16]/10 bg-white p-4 shadow-[0_6px_24px_-12px_rgba(5,11,22,0.15)]"
          >
            <div className="mb-2 flex items-start gap-3">
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-[#E8C766]/40 bg-[#E8C766]/15 text-[#E8C766]">
                <Scale size={15} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-[14px] font-semibold text-[#050B16]" dir="auto">
                  {l.full_name}
                </p>
                <p className="text-[11.5px] text-[#050B16]/55">
                  {l.court || l.region}
                </p>
              </div>
            </div>

            {l.address && (
              <p className="mb-1.5 text-[12px] leading-relaxed text-[#050B16]/70" dir="auto">
                {l.address}
              </p>
            )}

            {(l.phones || []).length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5" dir="ltr">
                {l.phones.map((p) => (
                  <a
                    key={p}
                    href={`tel:${p}`}
                    className="rounded-full border border-[#050B16]/10 bg-[#FAF7F0] px-2.5 py-1 text-[11.5px] font-medium text-[#050B16] transition-colors hover:border-[#050B16]/30"
                  >
                    {p}
                  </a>
                ))}
              </div>
            )}

            {l.tableau && (
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-[#050B16]/40">
                {l.tableau}
              </p>
            )}

            {l.maps_url && (
              <a
                href={l.maps_url}
                target="_blank"
                rel="noreferrer"
                className="text-[11.5px] font-medium text-[#050B16]/60 underline-offset-2 hover:text-[#050B16] hover:underline"
              >
                Voir sur la carte →
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Message                                                                   */
/* -------------------------------------------------------------------------- */
function Message({ msg, isLatestAssistant, onSpeak, ttsAvailable }) {
  const isUser = msg.role === "user";
  const [finished, setFinished] = useState(!isLatestAssistant);

  useEffect(() => {
    if (!isLatestAssistant) setFinished(true);
    else setFinished(false);
  }, [isLatestAssistant, msg.id]);

  const hasLawyerTool = msg.tool?.type === "lawyers";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE }}
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#050B16]">
          <Scale size={14} className="text-[#E8C766]" />
        </div>
      )}

      <div className="max-w-[80%] min-w-0">
        {isUser ? (
          <div className="rounded-2xl bg-[#050B16] px-4 py-2.5 text-[15px] font-medium leading-relaxed text-[#F7F3EA] shadow-[0_8px_30px_-10px_rgba(5,11,22,0.35)]">
            {msg.content}
          </div>
        ) : (
          <div className="text-[15px] leading-relaxed text-[#050B16]">
            {isLatestAssistant && !finished ? (
              <StreamingText text={msg.content} onDone={() => setFinished(true)} />
            ) : (
              <span className="whitespace-pre-wrap">{msg.content}</span>
            )}
          </div>
        )}

        {!isUser && finished && ttsAvailable && (
          <button
            type="button"
            onClick={() => onSpeak(msg.content, msg.lang || "fr")}
            className="mt-2 inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[#050B16]/45 transition-colors hover:text-[#050B16]"
            title="Écouter"
          >
            <Volume2 size={13} /> Écouter
          </button>
        )}

        {!isUser && hasLawyerTool && <LawyerCards tool={msg.tool} />}
      </div>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Carte rôle                                                                */
/* -------------------------------------------------------------------------- */
function ActorCard({ choice, icon: Icon, onPick }) {
  return (
    <motion.button
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 320, damping: 22 }}
      onClick={() => onPick(choice.id)}
      className="group flex flex-col gap-2.5 rounded-2xl border border-[#050B16]/10 bg-white/80 p-5 text-start backdrop-blur-xl transition-all hover:border-[#050B16]/25 hover:shadow-[0_15px_40px_-15px_rgba(5,11,22,0.2)]"
    >
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl border border-[#E8C766]/40 bg-[#E8C766]/15 text-[#E8C766] transition-all group-hover:bg-[#E8C766]/25">
          <Icon size={18} />
        </div>
        <div className="font-semibold text-[#050B16]">
          {choice.label_fr}
          <span className="mx-1.5 text-[#E8C766]">·</span>
          <span className="text-[#050B16]/60">{choice.label_ar}</span>
        </div>
      </div>
      <p className="text-[13px] leading-relaxed text-[#050B16]/60">
        {choice.desc_fr}
      </p>
    </motion.button>
  );
}

/* -------------------------------------------------------------------------- */
/*  Vue d'intro                                                               */
/* -------------------------------------------------------------------------- */
function IntroView({
  phase, greeting, choices, showChoices, onStreamingDone,
  onPick, sending, error, actorIcons,
}) {
  if (phase === "loading") {
    return (
      <div className="text-center">
        <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-[#050B16]">
          <Loader2 size={22} className="animate-spin text-[#E8C766]" />
        </div>
        <p className="text-sm font-medium text-[#050B16]/50">
          Chargement de l'assistant…
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl py-4 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: EASE }}
        className="mx-auto mb-6 grid h-16 w-16 place-items-center rounded-2xl bg-[#050B16] shadow-[0_15px_50px_-15px_rgba(5,11,22,0.35)]"
      >
        <Scale size={26} className="text-[#E8C766]" />
      </motion.div>

      <div className="min-h-[100px] text-xl font-bold leading-relaxed tracking-tight text-[#050B16] sm:text-2xl">
        {greeting && <StreamingText text={greeting} onDone={onStreamingDone} />}
      </div>

      <AnimatePresence>
        {showChoices && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="mt-8 grid gap-3 sm:grid-cols-2"
          >
            {choices.map((c) => (
              <ActorCard
                key={c.id}
                choice={c}
                icon={actorIcons[c.id] || Store}
                onPick={onPick}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {sending && (
        <div className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-[#050B16]/50">
          <Loader2 size={14} className="animate-spin" /> Dalil réfléchit…
        </div>
      )}

      {error && (
        <div className="mx-auto mt-4 inline-flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2 text-[13px] font-medium text-red-600">
          <AlertCircle size={14} /> {error}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Barre de saisie                                                           */
/* -------------------------------------------------------------------------- */
function InputBar({ input, setInput, onSend, onToggleRecording, recording, sending }) {
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="shrink-0 border-t border-[#050B16]/8 bg-[#FAF7F0]/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-3xl items-end gap-2 px-4 py-4">
        <button
          type="button"
          onClick={onToggleRecording}
          className={`grid h-11 w-11 shrink-0 place-items-center rounded-full transition-all ${
            recording
              ? "bg-red-500 text-white shadow-[0_0_30px_rgba(239,68,68,0.4)]"
              : "border border-[#050B16]/12 bg-white text-[#050B16]/60 hover:border-[#050B16]/25 hover:text-[#050B16]"
          }`}
          title={recording ? "Arrêter" : "Parler"}
        >
          {recording ? <MicOff size={18} /> : <Mic size={18} />}
        </button>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Posez votre question…"
          className="max-h-40 flex-1 resize-none rounded-2xl border border-[#050B16]/12 bg-white px-4 py-3 text-[15px] leading-relaxed text-[#050B16] outline-none transition-all placeholder:text-[#050B16]/35 focus:border-[#050B16]/30 focus:shadow-[0_0_0_4px_rgba(232,199,102,0.15)]"
          style={{ minHeight: "48px" }}
        />

        <button
          type="button"
          onClick={onSend}
          disabled={sending || !input.trim()}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#050B16] text-[#E8C766] shadow-[0_8px_30px_-8px_rgba(5,11,22,0.4)] transition-all hover:bg-[#050B16]/90 disabled:cursor-not-allowed disabled:opacity-40"
          title="Envoyer"
        >
          {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Page principale                                                           */
/* -------------------------------------------------------------------------- */
export default function WorkflowGuidance() {
  const [phase, setPhase] = useState("loading");
  const [messages, setMessages] = useState([]);
  const [choices, setChoices] = useState([]);
  const [showChoices, setShowChoices] = useState(false);
  const [actor, setActor] = useState(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const [ttsAvailable, setTtsAvailable] = useState(true);
  const [streamingId, setStreamingId] = useState(null);

  const scrollRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const actorIcons = { bailleur: Home, commercant: Store };
  const greeting = messages[0]?.content || "";

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  };

  useEffect(scrollToBottom, [messages, sending]);

  /* 1. Chargement de l'intro */
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.post("/features/workflow/intro/");
        const id = Date.now();
        setStreamingId(id);
        setMessages([{ id, role: "assistant", content: data.answer, lang: "fr", tool: null }]);
        setChoices(data.choices || []);
        setPhase("intro");
      } catch (e) {
        setError("Impossible de charger l'assistant.");
        setPhase("intro");
      }
    })();
  }, []);

  /* 2. Choix du rôle */
  const handlePick = async (actorId) => {
    setActor(actorId);
    setShowChoices(false);
    setPhase("actor");
    setSending(true);
    setError("");

    const history = messages.map(({ role, content }) => ({ role, content }));
    history.push({ role: "user", content: actorId });

    try {
      const { data } = await api.post("/features/workflow/choose-actor/", {
        actor: actorId,
        history,
      });
      const id = Date.now();
      setStreamingId(id);
      setMessages((prev) => [
        ...prev,
        {
          id: id - 1,
          role: "user",
          content:
            actorId === "bailleur"
              ? "Bailleur / المكري"
              : "Commerçant / التاجر",
        },
        {
          id,
          role: "assistant",
          content: data.answer,
          lang: data.lang || "fr",
          tool: data.tool || null,
        },
      ]);
      setPhase("chat");
    } catch (e) {
      setError("Erreur lors de la sélection du rôle.");
      setPhase("intro");
      setShowChoices(true);
    } finally {
      setSending(false);
    }
  };

  /* 3. Envoyer un message */
  const handleSend = async () => {
    const q = input.trim();
    if (!q || sending) return;
    setError("");
    setInput("");

    const userMsg = { id: Date.now(), role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    const history = messages
      .filter((m) => m.role !== "system")
      .map(({ role, content }) => ({ role, content }));

    try {
      const { data } = await api.post("/features/workflow/discuss/", {
        question: q,
        actor,
        history,
      });
      const id = Date.now() + 1;
      setStreamingId(id);
      setMessages((prev) => [
        ...prev,
        {
          id,
          role: "assistant",
          content: data.answer,
          lang: data.lang || "fr",
          tool: data.tool || null,
        },
      ]);
    } catch (e) {
      setError(e?.response?.data?.detail || "Erreur de communication.");
    } finally {
      setSending(false);
    }
  };

  /* 4. STT */
  const toggleRecording = async () => {
    if (recording) {
      recorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, "recording.webm");
        try {
          const { data } = await api.post("/features/workflow/stt/", form, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          if (data.text) setInput(data.text);
        } catch {
          setError("Transcription impossible.");
        }
      };
      mr.start();
      recorderRef.current = mr;
      setRecording(true);
    } catch {
      setError("Microphone indisponible.");
    }
  };

  /* 5. TTS */
  const handleSpeak = async (text, lang) => {
    try {
      const res = await api.post(
        "/features/workflow/tts/",
        { text, lang },
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(res.data);
      new Audio(url).play();
    } catch {
      setTtsAvailable(false);
    }
  };

  const isChat = phase === "chat";

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#FAF7F0] font-['Inter',system-ui,sans-serif] text-[#050B16] antialiased">
      <Nav />
      <div className={`${NAV_OFFSET} shrink-0`} aria-hidden />

      <main className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <motion.div
            aria-hidden
            animate={{ x: [0, 30, -20, 0], y: [0, -20, 20, 0] }}
            transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -left-40 -top-52 h-[520px] w-[520px] rounded-full bg-[#E8C766]/[0.18] blur-[160px]"
          />
          <motion.div
            aria-hidden
            animate={{ x: [0, -40, 20, 0], y: [0, 20, -20, 0] }}
            transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -bottom-56 -right-44 h-[520px] w-[520px] rounded-full bg-[#050B16]/[0.04] blur-[160px]"
          />
        </div>

        <AnimatePresence mode="wait">
          {!isChat ? (
            <motion.div
              key="intro"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.45, ease: EASE }}
              className={`relative z-10 ${SCROLL_AREA} flex items-center justify-center px-6 py-10`}
            >
              <IntroView
                phase={phase}
                greeting={greeting}
                choices={choices}
                showChoices={showChoices}
                onStreamingDone={() => setShowChoices(true)}
                onPick={handlePick}
                sending={sending}
                error={error}
                actorIcons={actorIcons}
              />
            </motion.div>
          ) : (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden"
            >
              <div ref={scrollRef} className={SCROLL_AREA}>
                <div className="mx-auto max-w-3xl space-y-5 px-4 py-8">
                  <AnimatePresence initial={false}>
                    {messages.map((m, i) => {
                      const isLatestAssistant =
                        m.role === "assistant" &&
                        i === messages.length - 1 &&
                        m.id === streamingId;
                      return (
                        <Message
                          key={m.id}
                          msg={m}
                          isLatestAssistant={isLatestAssistant}
                          onSpeak={handleSpeak}
                          ttsAvailable={ttsAvailable}
                        />
                      );
                    })}
                  </AnimatePresence>

                  {sending && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2 ps-11 text-sm font-medium text-[#050B16]/50"
                    >
                      <Loader2 size={15} className="animate-spin" />
                      Dalil réfléchit…
                    </motion.div>
                  )}

                  {error && (
                    <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2.5 text-[13px] font-medium text-red-600">
                      <AlertCircle size={15} /> {error}
                    </div>
                  )}
                </div>
              </div>

              <InputBar
                input={input}
                setInput={setInput}
                onSend={handleSend}
                onToggleRecording={toggleRecording}
                recording={recording}
                sending={sending}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <Footer />
    </div>
  );
}