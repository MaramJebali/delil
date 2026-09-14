// frontend-v2/src/routes/features/ContractUnderstanding.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Upload, FileText, Loader2, AlertCircle, CheckCircle2,
  XCircle, AlertTriangle, Sparkles, RefreshCw, Scale,
  ShieldCheck, Info, FileImage, Plus, Trash2, Play, ZoomIn,
} from "lucide-react";

import api from "../../api/axios";

const EASE = [0.22, 1, 0.36, 1];
const NAV_OFFSET = "h-[80px]";

const SCROLL_Y =
  "min-h-0 overflow-y-auto overscroll-contain " +
  "[scrollbar-width:thin] [scrollbar-color:rgba(5,11,22,0.18)_transparent] " +
  "[&::-webkit-scrollbar]:w-1.5 " +
  "[&::-webkit-scrollbar-track]:bg-transparent " +
  "[&::-webkit-scrollbar-thumb]:rounded-full " +
  "[&::-webkit-scrollbar-thumb]:bg-[#050B16]/15 " +
  "hover:[&::-webkit-scrollbar-thumb]:bg-[#050B16]/25";

// ═══════════════════════════════════════════════════════════════════
//  Field labels (FR)
// ═══════════════════════════════════════════════════════════════════
const FIELD_LABELS = {
  date_signature: "Date de signature",
  date_effet: "Date d'effet / entrée en jouissance",
  duree: "Durée",
  bailleur_nom_complet: "Nom complet du bailleur / propriétaire",
  bailleur_cin: "CIN / Passeport (bailleur)",
  bailleur_adresse: "Adresse (bailleur)",
  bailleur_matricule: "Matricule fiscal (bailleur)",
  preneur_nom_complet: "Nom complet du preneur / gérant",
  preneur_cin: "CIN / Passeport (preneur)",
  preneur_adresse: "Adresse (preneur)",
  preneur_matricule: "Matricule fiscal (preneur)",
  fonds_description: "Description du fonds de commerce",
  fonds_adresse: "Adresse d'exploitation du fonds",
  fonds_activite: "Nature de l'activité autorisée",
  fonds_ancien_rc: "Numéro d'immatriculation RC (fonds)",
  fonds_nouveau_rc: "Nouveau numéro RC (fonds)",
  redevance_montant: "Montant de la redevance",
  redevance_periodicite: "Périodicité de la redevance",
  depot_garantie: "Dépôt de garantie",
  loyer_montant: "Montant du loyer",
  adresse_bien: "Adresse du bien loué",
  activite_autorisee: "Activité autorisée",
  chiffre_affaires: "Chiffre d'affaires",
  benefices: "Bénéfices",
  bail_details: "Détails du bail",
  clause_nantissements: "État des inscriptions / nantissements",
  clause_renouvellement: "Clause de renouvellement",
  clause_resiliation: "Clause de résiliation",
  clause_sous_location: "Clause de sous-location",
  clause_ameliorations: "Clause d'améliorations",
  clause_duree_interdiction: "Clause de destination / non-modification",
  clause_dissipation: "Clause de non-dissipation",
  clause_publication: "Clause de publication",
  avocat_redacteur: "Avocat rédacteur",
  avocat_consultation_rc: "Consultation RC (avocat)",
  avocat_information_parties: "Information des parties (avocat)",
  avocat_formalites: "Formalités indiquées (avocat)",
  mention_gérant_libre: "Mention 'gérant libre' sur documents",
  signatures: "Signatures",
};

// ═══════════════════════════════════════════════════════════════════
//  Nav — exactly the same as WorkflowGuidance
// ═══════════════════════════════════════════════════════════════════
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
              <FileText size={16} className="text-[#E8C766]" />
            </div>
            <span className="text-[15px] font-semibold tracking-tight text-[#F7F3EA]">
              Compréhension du contrat
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

// ═══════════════════════════════════════════════════════════════════
//  Footer — exactly the same as WorkflowGuidance
// ═══════════════════════════════════════════════════════════════════
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

// ═══════════════════════════════════════════════════════════════════
//  Gradient scanner
// ═══════════════════════════════════════════════════════════════════
function GradientScanner() {
  return (
    <div className="absolute inset-0 pointer-events-none z-30 overflow-hidden rounded-2xl">
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(232,199,102,0.10), transparent 70%)",
        }}
        animate={{ opacity: [0.4, 0.9, 0.4] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute left-0 right-0"
        style={{
          height: "140px",
          background:
            "linear-gradient(to bottom, " +
            "rgba(232,199,102,0) 0%, " +
            "rgba(232,199,102,0.15) 20%, " +
            "rgba(244,224,168,0.55) 45%, " +
            "rgba(232,199,102,0.95) 50%, " +
            "rgba(244,224,168,0.55) 55%, " +
            "rgba(232,199,102,0.15) 80%, " +
            "rgba(232,199,102,0) 100%)",
          filter: "blur(2px)",
          mixBlendMode: "screen",
        }}
        animate={{ top: ["-140px", "100%"] }}
        transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute left-0 right-0 h-[3px]"
        style={{
          background:
            "linear-gradient(90deg, transparent, #F4E0A8, #E8C766, #F4E0A8, transparent)",
          boxShadow: "0 0 28px 6px rgba(232,199,102,0.85)",
        }}
        animate={{ top: ["0%", "100%"] }}
        transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Upload zone
// ═══════════════════════════════════════════════════════════════════
function UploadZone({ onFiles }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) onFiles(files);
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onClick={() => inputRef.current?.click()}
      className={`flex h-full w-full cursor-pointer flex-col items-center justify-center gap-5
                  rounded-3xl border-2 border-dashed p-8 text-center backdrop-blur-xl
                  transition-all duration-300
                  ${dragOver
                    ? "border-[#E8C766] bg-white shadow-[0_20px_60px_-20px_rgba(232,199,102,0.6)]"
                    : "border-[#050B16]/15 bg-white/70 hover:border-[#E8C766]/60"}`}
    >
      <motion.div
        whileHover={{ scale: 1.05 }}
        className="grid h-16 w-16 place-items-center rounded-2xl bg-[#050B16] text-[#E8C766] shadow-[0_10px_30px_-10px_rgba(5,11,22,0.4)]"
      >
        <Upload size={26} />
      </motion.div>

      <div className="max-w-xs">
        <p className="text-[15px] font-semibold text-[#050B16]">
          Déposez votre contrat ici
        </p>
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-[#050B16]/60">
          PDF ou images (JPG, PNG, WEBP)
          <br />
          Un ou plusieurs fichiers acceptés
        </p>
      </div>

      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-full bg-[#050B16] px-5 py-2.5 text-[13px] font-semibold text-[#E8C766] shadow-[0_6px_20px_-8px_rgba(5,11,22,0.4)] transition-all hover:bg-[#050B16]/90"
        onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
      >
        Choisir des fichiers
      </button>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,application/pdf,image/*"
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  File preview
// ═══════════════════════════════════════════════════════════════════
function FilePreview({ files, extracting, onReset, onRemove, onAddMore }) {
  const previews = useMemo(
    () =>
      files.map((f) => {
        const isImage = f.type.startsWith("image/");
        const url = URL.createObjectURL(f);
        return { file: f, isImage, url };
      }),
    [files]
  );

  useEffect(() => {
    return () => previews.forEach((p) => URL.revokeObjectURL(p.url));
  }, [previews]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium text-[#050B16]/60">
          {files.length} document{files.length > 1 ? "s" : ""}
        </span>
        <div className="flex gap-2">
          <button
            onClick={onAddMore}
            disabled={extracting}
            className="inline-flex items-center gap-1 rounded-full border border-[#050B16]/12 bg-white px-3 py-1.5 text-[11.5px] font-medium text-[#050B16]/70 transition-all hover:border-[#050B16]/25 hover:text-[#050B16] disabled:opacity-50"
          >
            <Plus size={12} /> Ajouter
          </button>
          <button
            onClick={onReset}
            disabled={extracting}
            className="inline-flex items-center gap-1 rounded-full border border-[#050B16]/12 bg-white px-3 py-1.5 text-[11.5px] font-medium text-[#050B16]/70 transition-all hover:border-[#050B16]/25 hover:text-[#050B16] disabled:opacity-50"
          >
            <RefreshCw size={12} /> Effacer
          </button>
        </div>
      </div>

      <div className="relative">
        <div className="space-y-3">
          {previews.map((p, i) => (
            <div
              key={i}
              className="relative overflow-hidden rounded-2xl border border-[#050B16]/10 bg-white shadow-[0_12px_36px_-14px_rgba(5,11,22,0.25)]"
            >
              <div className="flex items-center gap-2 border-b border-[#050B16]/8 bg-[#FAF7F0] px-3 py-2 text-[11.5px] text-[#050B16]/70">
                {p.isImage ? <FileImage size={13} /> : <FileText size={13} />}
                <span className="truncate flex-1 font-medium">{p.file.name}</span>
                <span className="text-[#050B16]/45">
                  {(p.file.size / 1024).toFixed(0)} KB
                </span>
                {!extracting && (
                  <button
                    onClick={() => onRemove(i)}
                    className="text-red-500 transition-colors hover:text-red-600"
                    title="Retirer"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>

              <div className="relative w-full bg-white">
                {p.isImage ? (
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="group relative block"
                  >
                    <img
                      src={p.url}
                      alt={p.file.name}
                      className="mx-auto block max-w-full bg-white object-contain"
                      style={{ maxHeight: "70vh" }}
                    />
                    <div className="absolute right-2 top-2 rounded-full bg-[#050B16]/80 p-1.5 text-[#E8C766] opacity-0 transition-opacity group-hover:opacity-100">
                      <ZoomIn size={13} />
                    </div>
                  </a>
                ) : (
                  <object
                    data={p.url}
                    type="application/pdf"
                    className="block w-full bg-white"
                    style={{ height: "70vh" }}
                  >
                    <div className="grid h-[400px] place-items-center bg-white text-sm text-[#050B16]/60">
                      Aperçu PDF indisponible — <a href={p.url} target="_blank" rel="noreferrer" className="ms-1 underline">ouvrir dans un nouvel onglet</a>
                    </div>
                  </object>
                )}
              </div>
            </div>
          ))}
        </div>

        <AnimatePresence>
          {extracting && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="pointer-events-none absolute inset-0"
            >
              <GradientScanner />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {extracting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center justify-center gap-2 rounded-xl border border-[#050B16]/10 bg-white/80 py-2.5 text-[12.5px] font-medium text-[#050B16]/75 backdrop-blur-md"
          >
            <Loader2 size={15} className="animate-spin text-[#E8C766]" />
            Analyse en cours…
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Field input
// ═══════════════════════════════════════════════════════════════════
function FieldInput({ fieldKey, value, onChange }) {
  const label = FIELD_LABELS[fieldKey] || fieldKey.replace(/_/g, " ");
  const isLong = [
    "fonds_description", "bail_details", "clause_resiliation",
    "clause_renouvellement", "clause_sous_location",
    "clause_ameliorations", "clause_duree_interdiction",
    "clause_dissipation", "clause_publication",
  ].includes(fieldKey);

  const cls =
    "mt-1 w-full rounded-xl border border-[#050B16]/12 bg-[#FAF7F0]/60 px-3 py-2 text-[13px] text-[#050B16] outline-none transition-all placeholder:text-[#050B16]/35 focus:border-[#E8C766] focus:bg-white focus:shadow-[0_0_0_4px_rgba(232,199,102,0.15)]";

  return (
    <div>
      <label className="text-[10.5px] font-medium uppercase tracking-wide text-[#050B16]/50">
        {label}
      </label>
      {isLong ? (
        <textarea
          value={value || ""}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          rows={2}
          className={cls + " resize-none"}
        />
      ) : (
        <input
          value={value || ""}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          className={cls}
        />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  InnerCard
// ═══════════════════════════════════════════════════════════════════
function InnerCard({ children, className = "" }) {
  return (
    <div
      className={
        "rounded-2xl border border-[#050B16]/8 bg-white/95 p-5 shadow-[0_10px_30px_-20px_rgba(5,11,22,0.25)] backdrop-blur-xl " +
        className
      }
    >
      {children}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Step 1 panel
// ═══════════════════════════════════════════════════════════════════
function Step1Panel({ data, editedFields, onFieldChange, onValidate, analyzing }) {
  const { identification, completeness, post_signature_formalities } = data;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="space-y-4"
    >
      <InnerCard className="border-[#E8C766]/40 bg-gradient-to-br from-[#E8C766]/15 via-white/95 to-white/95">
        <div className="mb-3 flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#E8C766]/25">
            <Sparkles size={15} className="text-[#050B16]" />
          </div>
          <h2 className="text-[14px] font-semibold text-[#050B16]">
            Vérifiez les informations extraites
          </h2>
        </div>
        <div className="grid grid-cols-2 gap-3 text-[13px]">
          <div>
            <p className="text-[10.5px] uppercase tracking-wide text-[#050B16]/50">
              Type de contrat
            </p>
            <p className="mt-0.5 font-semibold text-[#050B16]">
              {identification.contract_type || "—"}
            </p>
          </div>
          <div>
            <p className="text-[10.5px] uppercase tracking-wide text-[#050B16]/50">
              Langue
            </p>
            <p className="mt-0.5 font-semibold text-[#050B16]">
              {identification.language || "—"}
            </p>
          </div>
        </div>
        {identification.summary_short && (
          <p className="mt-3 border-t border-[#050B16]/8 pt-3 text-[13px] leading-relaxed text-[#050B16]/75">
            {identification.summary_short}
          </p>
        )}
      </InnerCard>

      <InnerCard>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-[13px] font-semibold text-[#050B16]">
            <ShieldCheck size={15} className="text-[#E8C766]" />
            Conformité RNE / Code de Commerce
          </h3>
          <span className="rounded-full bg-[#050B16]/5 px-2.5 py-0.5 text-[11px] font-semibold text-[#050B16]/70">
            {completeness.present_count}/{completeness.total}
          </span>
        </div>

        {completeness.blocking_missing?.length > 0 && (
          <div className="mb-3">
            <p className="mb-1.5 flex items-center gap-1 text-[11.5px] font-semibold text-red-600">
              <XCircle size={12} /> Manquants obligatoires
            </p>
            <ul className="space-y-1">
              {completeness.blocking_missing.map((lbl, i) => (
                <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-[#050B16]/80">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-red-500" /> {lbl}
                </li>
              ))}
            </ul>
          </div>
        )}

        {completeness.warning_missing?.length > 0 && (
          <div className="mb-3">
            <p className="mb-1.5 flex items-center gap-1 text-[11.5px] font-semibold text-amber-600">
              <AlertTriangle size={12} /> À compléter
            </p>
            <ul className="space-y-1">
              {completeness.warning_missing.map((lbl, i) => (
                <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-[#050B16]/80">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-500" /> {lbl}
                </li>
              ))}
            </ul>
          </div>
        )}

        {completeness.present?.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1 text-[11.5px] font-semibold text-emerald-600">
              <CheckCircle2 size={12} /> Présents ({completeness.present_count})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {completeness.present.slice(0, 8).map((it, i) => (
                <span
                  key={i}
                  className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10.5px] font-medium text-emerald-700"
                >
                  {it.label_fr?.slice(0, 40) || it.id}
                </span>
              ))}
            </div>
          </div>
        )}
      </InnerCard>

      <InnerCard>
        <h3 className="mb-3 text-[13px] font-semibold text-[#050B16]">
          Champs extraits (modifiables)
        </h3>
        <div className="max-h-[380px] space-y-3 overflow-y-auto pe-1">
          {Object.keys(editedFields || {}).map((k) => (
            <FieldInput
              key={k}
              fieldKey={k}
              value={editedFields[k]}
              onChange={onFieldChange}
            />
          ))}
        </div>
      </InnerCard>

      {post_signature_formalities?.length > 0 && (
        <div className="rounded-2xl border border-[#E8C766]/40 bg-[#E8C766]/10 p-5 backdrop-blur-xl">
          <h3 className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-[#050B16]">
            <Info size={15} className="text-[#E8C766]" />
            Formalités après signature
          </h3>
          <ul className="space-y-1.5">
            {post_signature_formalities.map((f, i) => (
              <li key={i} className="text-[12.5px] leading-relaxed text-[#050B16]/85">
                <span className="me-1.5 text-[#E8C766]">•</span>
                {f.label_fr}
                {f.legal_basis && (
                  <span className="ms-1 text-[11px] text-[#050B16]/50">
                    ({f.legal_basis})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={onValidate}
        disabled={analyzing}
        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#E8C766] py-3.5 text-[13.5px] font-semibold text-[#050B16] shadow-[0_10px_30px_-8px_rgba(232,199,102,0.6)] transition-all hover:bg-[#F4E0A8] hover:shadow-[0_14px_36px_-10px_rgba(232,199,102,0.7)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {analyzing ? (
          <>
            <Loader2 size={15} className="animate-spin" /> Analyse en cours…
          </>
        ) : (
          <>
            Valider et analyser <ArrowLeft size={15} className="rotate-180" />
          </>
        )}
      </button>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Step 2 panel
// ═══════════════════════════════════════════════════════════════════
function Step2Panel({ data, contractContext }) {
  const [tab, setTab] = useState("bailleur");
  const { validation, assessment, explanation, suggested_questions } = data;

  const riskBadge =
    assessment.risk_level === "high"
      ? "bg-red-50 text-red-700 border-red-200"
      : assessment.risk_level === "medium"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-emerald-50 text-emerald-700 border-emerald-200";

  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="rounded-2xl border border-[#E8C766]/40 bg-gradient-to-br from-[#E8C766]/15 via-white/95 to-white/95 p-5 shadow-[0_10px_30px_-20px_rgba(5,11,22,0.25)] backdrop-blur-xl"
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#E8C766]/25">
              <Scale size={15} className="text-[#050B16]" />
            </div>
            <h2 className="text-[14px] font-semibold text-[#050B16]">
              Analyse du contrat
            </h2>
          </div>
          <span className={`rounded-full border px-3 py-1 text-[10.5px] font-semibold uppercase tracking-wide ${riskBadge}`}>
            Risque : {assessment.risk_level || "—"}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 text-[13px]">
          <div>
            <p className="text-[10.5px] uppercase tracking-wide text-[#050B16]/50">
              Conforme
            </p>
            <p className="mt-0.5 font-semibold text-[#050B16]">
              {assessment.compliant === true
                ? "Oui"
                : assessment.compliant === false
                ? "Non"
                : "—"}
            </p>
          </div>
        </div>
      </motion.div>

      {validation.missing_legal?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05, duration: 0.4, ease: EASE }}
          className="rounded-2xl border border-red-300/60 bg-red-50/95 p-5 shadow-[0_10px_30px_-20px_rgba(5,11,22,0.25)] backdrop-blur-xl"
        >
          <h3 className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-red-700">
            <AlertTriangle size={14} /> Éléments manquants
          </h3>
          <ul className="space-y-1">
            {validation.missing_legal.map((lbl, i) => (
              <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-red-900/80">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-red-500" /> {lbl}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {assessment.risks?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, duration: 0.4, ease: EASE }}
        >
          <InnerCard>
            <h3 className="mb-3 text-[13px] font-semibold text-[#050B16]">
              Points d'attention
            </h3>
            <div className="space-y-3">
              {assessment.risks.map((r, i) => (
                <div key={i} className="border-s-2 border-[#E8C766] ps-3">
                  <p className="text-[13px] font-semibold text-[#050B16]">{r.issue}</p>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-[#050B16]/70">
                    {r.detail}
                  </p>
                  {r.article && (
                    <p className="mt-1 inline-block rounded-md bg-[#E8C766]/20 px-2 py-0.5 text-[10.5px] font-medium text-[#050B16]/70">
                      {r.article}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </InnerCard>
        </motion.div>
      )}

      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.15, duration: 0.4, ease: EASE }}
      >
        <InnerCard>
          <h3 className="mb-3 text-[13px] font-semibold text-[#050B16]">
            Ce que cela signifie pour vous
          </h3>
          <div className="mb-4 flex gap-2">
            <button
              onClick={() => setTab("bailleur")}
              className={`rounded-xl px-3.5 py-1.5 text-[12px] font-semibold transition-all ${
                tab === "bailleur"
                  ? "bg-[#050B16] text-[#E8C766]"
                  : "bg-[#050B16]/5 text-[#050B16]/70 hover:bg-[#050B16]/10"
              }`}
            >
              Propriétaire
            </button>
            <button
              onClick={() => setTab("commercant")}
              className={`rounded-xl px-3.5 py-1.5 text-[12px] font-semibold transition-all ${
                tab === "commercant"
                  ? "bg-[#050B16] text-[#E8C766]"
                  : "bg-[#050B16]/5 text-[#050B16]/70 hover:bg-[#050B16]/10"
              }`}
            >
              Gérant
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="space-y-3"
            >
              {explanation[`for_${tab}`]?.what_it_means && (
                <p className="text-[13px] leading-relaxed text-[#050B16]/85">
                  {explanation[`for_${tab}`].what_it_means}
                </p>
              )}
              {explanation[`for_${tab}`]?.your_rights?.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                    Vos droits
                  </p>
                  <ul className="space-y-1">
                    {explanation[`for_${tab}`].your_rights.map((r, i) => (
                      <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-[#050B16]/80">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {explanation[`for_${tab}`]?.to_avoid?.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-red-600">
                    À éviter
                  </p>
                  <ul className="space-y-1">
                    {explanation[`for_${tab}`].to_avoid.map((r, i) => (
                      <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-[#050B16]/80">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-red-500" /> {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </InnerCard>
      </motion.div>

      {suggested_questions?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.4, ease: EASE }}
        >
          <InnerCard>
            <h3 className="mb-3 text-[13px] font-semibold text-[#050B16]">
              Questions suggérées
            </h3>
            <div className="flex flex-col gap-2">
              {suggested_questions.map((q, i) => (
                <SuggestedQuestion key={i} question={q} contractContext={contractContext} />
              ))}
            </div>
          </InnerCard>
        </motion.div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Suggested question
// ═══════════════════════════════════════════════════════════════════
function SuggestedQuestion({ question, contractContext }) {
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/features/contract/ask/", {
        question,
        contract_context: contractContext,
      });
      setAnswer(data.answer);
    } catch {
      setAnswer("Erreur de communication avec l'assistant.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <button
        onClick={handleClick}
        disabled={loading}
        className="w-full rounded-xl border border-[#050B16]/10 bg-[#FAF7F0]/80 px-3.5 py-2.5 text-start text-[12.5px] font-medium text-[#050B16] transition-all hover:border-[#E8C766]/60 hover:bg-[#E8C766]/10 disabled:opacity-50"
      >
        {loading ? (
          <span className="inline-flex items-center gap-2 text-[#050B16]/60">
            <Loader2 size={12} className="animate-spin text-[#E8C766]" /> Analyse…
          </span>
        ) : (
          question
        )}
      </button>
      {answer && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="ms-2 mt-2 whitespace-pre-wrap border-s-2 border-[#E8C766] ps-3 text-[12.5px] leading-relaxed text-[#050B16]/85"
        >
          {answer}
        </motion.div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Main page
// ═══════════════════════════════════════════════════════════════════
export default function ContractUnderstanding() {
  const [files, setFiles] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [step1, setStep1] = useState(null);
  const [editedFields, setEditedFields] = useState({});
  const [analyzing, setAnalyzing] = useState(false);
  const [step2, setStep2] = useState(null);
  const [error, setError] = useState("");

  const handleFiles = (newFiles) => {
    setError("");
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemove = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setStep1(null);
    setStep2(null);
    setEditedFields({});
  };

  const handleReset = () => {
    setFiles([]);
    setStep1(null);
    setStep2(null);
    setEditedFields({});
    setError("");
  };

  const handleStart = async () => {
    if (!files.length) return;
    setExtracting(true);
    setError("");
    try {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      const { data } = await api.post("/features/contract/extract/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setStep1(data);
      setEditedFields(data.identification?.fields || {});
    } catch (e) {
      setError(e?.response?.data?.detail || "Erreur lors de l'extraction.");
    } finally {
      setExtracting(false);
    }
  };

  const handleFieldChange = (key, value) => {
    setEditedFields((prev) => ({ ...prev, [key]: value }));
  };

  const handleValidate = async () => {
    if (!step1) return;
    setAnalyzing(true);
    setError("");
    try {
      const identification = { ...step1.identification, fields: editedFields };
      const { data } = await api.post("/features/contract/analyze/", {
        identification,
        completeness: step1.completeness,
      });
      setStep2(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Erreur lors de l'analyse.");
    } finally {
      setAnalyzing(false);
    }
  };

  const contractContext = useMemo(
    () =>
      step1
        ? { identification: { ...step1.identification, fields: editedFields } }
        : null,
    [step1, editedFields]
  );

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#FAF7F0] font-['Inter',system-ui,sans-serif] text-[#050B16] antialiased">
      <Nav />
      <div className={`${NAV_OFFSET} shrink-0`} aria-hidden />

      <main className="relative flex min-h-0 flex-1 overflow-hidden">
        {/* Soft halos — same as WorkflowGuidance */}
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

        {/* Two equal halves */}
        <div className="relative z-10 flex min-h-0 flex-1 overflow-hidden">
          {/* LEFT — documents */}
          <div className={`w-1/2 shrink-0 grow-0 border-e border-[#050B16]/8 ${SCROLL_Y} p-5 lg:p-6`}>
            <div className="flex h-full flex-col">
              {files.length === 0 ? (
                <UploadZone onFiles={handleFiles} />
              ) : (
                <>
                  <FilePreview
                    files={files}
                    extracting={extracting}
                    onReset={handleReset}
                    onRemove={handleRemove}
                    onAddMore={() => {
                      const inp = document.createElement("input");
                      inp.type = "file";
                      inp.multiple = true;
                      inp.accept =
                        ".pdf,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,application/pdf,image/*";
                      inp.onchange = (e) => {
                        const fs = Array.from(e.target.files || []);
                        if (fs.length) handleFiles(fs);
                      };
                      inp.click();
                    }}
                  />

                  {!step1 && !extracting && (
                    <motion.button
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={handleStart}
                      className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-[#E8C766] py-3.5 text-[13.5px] font-semibold text-[#050B16] shadow-[0_10px_30px_-8px_rgba(232,199,102,0.6)] transition-all hover:bg-[#F4E0A8] hover:shadow-[0_14px_36px_-10px_rgba(232,199,102,0.7)]"
                    >
                      <Play size={15} /> Démarrer l'analyse
                    </motion.button>
                  )}
                </>
              )}

              {error && (
                <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2.5 text-[12.5px] font-medium text-red-600">
                  <AlertCircle size={14} /> {error}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT — results */}
          <div className={`w-1/2 shrink-0 grow-0 ${SCROLL_Y} p-5 lg:p-6`}>
            {!step1 && !extracting && (
              <div className="grid h-full place-items-center text-center">
                <div className="max-w-xs rounded-3xl border border-[#050B16]/8 bg-white/70 p-8 backdrop-blur-xl">
                  <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-[#050B16]">
                    <Sparkles size={24} className="text-[#E8C766]" />
                  </div>
                  <p className="text-[13.5px] font-medium leading-relaxed text-[#050B16]/70">
                    Importez un ou plusieurs documents à gauche,
                    <br />
                    puis cliquez sur « Démarrer l'analyse ».
                  </p>
                </div>
              </div>
            )}

            {extracting && !step1 && (
              <div className="grid h-full place-items-center text-center">
                <div className="rounded-3xl border border-[#050B16]/8 bg-white/70 p-8 backdrop-blur-xl">
                  <Loader2 size={28} className="mx-auto mb-3 animate-spin text-[#E8C766]" />
                  <p className="text-[13px] font-medium text-[#050B16]/70">
                    Lecture et extraction des champs…
                  </p>
                </div>
              </div>
            )}

            {step1 && !step2 && (
              <Step1Panel
                data={step1}
                editedFields={editedFields}
                onFieldChange={handleFieldChange}
                onValidate={handleValidate}
                analyzing={analyzing}
              />
            )}

            {step2 && <Step2Panel data={step2} contractContext={contractContext} />}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}