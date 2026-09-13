"""
Agent — Dalil · Feature 2 (Workflow Guidance).

Flow (button-driven actor selection — no free-text detection)
──────────────────────────────────────────────────────────────
PHASE 1 · INTRO      : intro()                    → French greeting + 2 choices
PHASE 2 · CONFIRM    : choose_actor(actor)        → acknowledgment + invitation
PHASE 3 · DISCUSSION : discuss(question, actor)   → RAG + LLM + tools (conversational)
TOOLS                : lawyers | workflow | format_contract
VOICE                : ask_voice(audio, actor)    → STT → discuss → TTS

Intent routing
──────────────
- workflow        : keyword + hard-trigger (deterministic)
- format_contract : keyword (deterministic)
- lawyers         : deterministic ("avocat"/"محامي" + no denial) → LLM fallback
- region          : deterministic scan of the 24 Tunisian governorates
- none            : everything else

LLM       : Groq primary → Mistral fallback
STT + TTS : features/ai/voice.py
Language  : FR / AR auto-detected (Phase 2/3 only — Phase 1 is FR only)
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")

from . import rag  # noqa: E402

try:
    from . import voice as _voice
    _HAS_VOICE = True
except Exception:
    _HAS_VOICE = False

try:
    from . import tools as _tools
    _HAS_TOOLS = True
except Exception as _e:
    print(f"⚠️  tools.py not loaded: {_e}")
    _HAS_TOOLS = False


# ═══════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

LLM_PRIMARY_MODEL  = os.getenv("LLM_PRIMARY_MODEL",  "qwen/qwen3.8-27b")
LLM_FAST_MODEL     = os.getenv("LLM_FAST_MODEL",     "openai/gpt-oss-20b")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "ministral-8b-latest")

ACTOR_LABELS = {
    "bailleur": {
        "label_fr": "Bailleur",
        "label_ar": "المكري",
        "desc_fr": "Propriétaire du local (ex. propriétaire d'un café loué à un commerçant).",
        "desc_ar": "مالك المحل (مثال: مالك مقهى مكري لتاجر).",
    },
    "commercant": {
        "label_fr": "Commerçant",
        "label_ar": "التاجر",
        "desc_fr": "Locataire / exploitant du fonds de commerce (ex. gérant du café).",
        "desc_ar": "مكتري / مستغل الأصل التجاري (مثال: صاحب المقهى).",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _clean(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _compress_history(history: list, keep_last: int = 2) -> list:
    if not history:
        return []
    return history[-(keep_last * 2):]


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _normalize(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")
    s = _strip_accents(s)
    s = re.sub(r"[\u064B-\u065F\u0670]", "", s)
    s = re.sub(r"[إأآا]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي")
    s = s.replace("ة", "ه")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _detect_lang_smart(text: str) -> str:
    if not text:
        return "fr"
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    latin_chars  = sum(1 for c in text if "a" <= c.lower() <= "z")
    if arabic_chars > 3 and arabic_chars > latin_chars:
        return "ar"
    if latin_chars > 3 and latin_chars >= arabic_chars:
        return "fr"
    try:
        out = _call_llm(
            [{"role": "user", "content": (
                "Reply with ONLY one word.\n"
                "Which language is this message in: French or Arabic?\n"
                "Answer 'fr' or 'ar'.\n\n"
                f'Message: "{text}"'
            )}],
            model=LLM_FAST_MODEL,
            temperature=0.0,
            max_tokens=5,
        ).strip().lower()
        return "ar" if "ar" in out else "fr"
    except Exception:
        return "fr"


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        chunk = re.sub(r",\s*([\]}])", r"\1", m.group(0))
        try:
            data = json.loads(chunk)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return None


# ═══════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are Dalil (دليل), the legal assistant embedded in the Workflow Guidance service of the Dalil platform.

## Your personality
You are a warm, patient legal guide — not a search engine.
You take time to understand the user's situation, explain what it means for THEM specifically, and walk them through what to do next.
You never just list facts. You always tie facts back to their situation and their next step.

## Scope
You guide the user step by step through procedures related to Tunisian commercial law — specifically fonds de commerce (الأصل التجاري) governed by:
- Loi n° 77-37 du 25 mai 1977 (baux commerciaux / الكراء التجاري)
- Code de Commerce, Livre II (fonds de commerce / المجلة التجارية، الكتاب الثاني)

## The conversation has 3 phases. You will be told which phase is active.

### PHASE 1 — INTRO
Write the greeting ENTIRELY IN FRENCH. Do NOT use Arabic paragraphs.
Do NOT use markdown bold (**), italics (*), or headers (#). Plain text only.

The frontend will display the two actor choices as clickable cards BELOW your text. So:
- Do NOT list the two roles.
- Do NOT ask the user to reply with "1" or "2".
- Just greet and ask the user to pick their role using the buttons below.

Format (follow exactly — no lists, no numbers):

Bonjour, je suis Dalil (دليل). Je vais vous guider pas à pas dans les procédures relatives au droit commercial tunisien.

Pour commencer, merci de sélectionner votre rôle ci-dessous.

Do NOT answer any legal question on this turn.

### PHASE 2 — CONFIRM
The user has chosen their role. You will be told which one (bailleur or commercant).
Acknowledge warmly in ONE short sentence, in FRENCH by default.
Then invite them to describe their situation, giving 3–4 short examples in French.

Example:
"Très bien. Décrivez votre situation : renouvellement, refus de renouvellement, impayé, sous-location, ou une question de délais."

Do NOT answer any legal question on this turn. Stop and wait.

### PHASE 3 — DISCUSSION (the heart of the assistant)

## The three moves of every answer

**Move 1 — Accuse réception (1 sentence)**
Acknowledge the user's question in your own words. Show you understood.

**Move 2 — Le cœur de la réponse (structured, but conversational)**
Give the substance. Speak TO the user (vous / أنت). Explain WHY, not just WHAT.

**Move 3 — Invitation à continuer (1-2 sentences)**
End with ONE of:
- A concrete next action ("Prochaine étape" / "الخطوة التالية")
- OR a gentle follow-up question if the situation is still ambiguous
- OR an offer to go deeper on one sub-point.

Never end flatly. Always leave a door open.

## Answer length — MATCH THE QUESTION

Default behaviour:
- Simple question ("C'est quoi un fonds de commerce ?") → 2–4 SHORT sentences. No bullets. No "Réponse / Articles cités / Prochaine étape" headers.
- Real enquiry that needs structure ("Puis-je refuser le renouvellement ?") → use the structured format below with 3–4 bullets.
- User explicitly asks for detail ("explique en détail", "donne-moi tout", "بالتفصيل") → go up to 8 bullets, add nuance.

DO NOT overload a simple question with a 6-bullet structured answer. Talk like a helpful human, not a legal template.

## When a TOOL was executed
The system may tell you a tool was executed. Weave it in naturally:

- **"lawyers"** → Lawyer cards are shown below your answer.
  Move 1: acknowledge you found suitable lawyers nearby.
  Move 2: explain WHAT to prepare before contacting them (documents, timeline, questions to ask).
  Move 3: invite them to look at the cards and contact 2–3 of them.
  If the system says NO region was detected, add ONE short sentence inviting them to specify their city to refine — but do NOT block on it, the cards are already shown.
  Do NOT list the lawyers again in your text.

- **"workflow"** → The step-by-step frame is already shown to the user below your answer.
  Your text is ONLY Move 1 (acknowledgment) + Move 3 (next step + follow-up).
  Do NOT repeat the steps. Do NOT re-frame them.
  In Move 3, tell them WHICH step to start with today and WHY.

- **"format_contract"** → A contract skeleton is shown below your answer.
  Move 1: acknowledge the contract type.
  Move 2: give 1–2 practical drafting / negotiation tips (what's often missing, what protects them).
  Move 3: suggest a next action.
  Do NOT repeat the skeleton.

## Language rules (STRICT)
- PHASE 1 (INTRO) is ALWAYS in FRENCH only.
- PHASE 2 and PHASE 3: reply 100% in the user's latest-message language.
- Never mix languages in the same sentence.

## Formatting rules (STRICT — all phases)
- Do NOT use markdown bold (**), italics (*), or headers (#).
- Use plain text.
- Numbered lists: "1. ", "2. ", …
- Bullets: "- " at the start of the line.
- Blank line between sections.
- Keep it readable — not a wall of text.

## Structured format (PHASE 3 — ONLY when the answer needs structure)

If the user's language is French:

<Move 1 — one sentence>

Réponse
- point 1
- point 2
- point 3

Articles cités
- Article X de la loi 77-37

Prochaine étape
- <one concrete action>

<Move 3 — optional follow-up>

If the user's language is Arabic:

<Move 1 — sentence in Arabic>

الإجابة
- نقطة 1
- نقطة 2

الفصول المعتمدة
- الفصل X من القانون 77-37

الخطوة التالية
- <إجراء واحد>

<Move 3 — سؤال متابعة إن لزم>

## Hard rules
- Rely ONLY on the retrieved context. If it doesn't cover the question, say so and suggest consulting an avocat / tribunal.
- Always cite article(s) when you make a legal claim.
- Never invent article numbers, deadlines, or amounts.
- Always finish with the next-step or follow-up line.
- Never sound robotic. Never say "Voici la réponse :" or "Selon le contexte récupéré :".
- Sound like a trusted advisor who knows the law and cares about the user's outcome.
"""


# ═══════════════════════════════════════════════════════════════════
#  LLM CLIENTS
# ═══════════════════════════════════════════════════════════════════

def _groq_client():
    return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)


def _mistral_client():
    return OpenAI(base_url="https://api.mistral.ai/v1", api_key=MISTRAL_API_KEY)


def _call_llm(messages, model=None, temperature=0.2, max_tokens=1500) -> str:
    try:
        r = _groq_client().chat.completions.create(
            model=model or LLM_PRIMARY_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        print(f"⚠️  Groq failed: {type(e).__name__} — {str(e)[:140]}")
    try:
        r = _mistral_client().chat.completions.create(
            model=LLM_FALLBACK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        print(f"❌ Mistral failed too: {str(e)[:140]}")
        raise


# ═══════════════════════════════════════════════════════════════════
#  INTENT DETECTION
#  ─ workflow & format_contract : keyword + hard triggers (deterministic)
#  ─ lawyers                    : deterministic word + denial check → LLM fallback
#  ─ region                     : deterministic scan of 24 governorates
# ═══════════════════════════════════════════════════════════════════

_INTENT_PATTERNS = {
    "format_contract": [
        (r"\bredig", 10), (r"\bredaction\b", 10),
        (r"\bclause", 8), (r"\bmodele\b", 8), (r"\btemplate\b", 8),
        (r"\bstructure\s+du\s+contrat", 12),
        (r"\bmentions?\s+obligatoires?", 10),
        (r"\bdoit\s+(contenir|comprendre)", 8),
        (r"\bque\s+doit\s+(contenir|comprendre)", 10),
        (r"\bcomment\s+formuler", 8),
        (r"\bsquelette\b", 8),
        (r"صياغ", 10), (r"صيغ", 8), (r"بنود", 10),
        (r"نموذج", 8), (r"بنيه", 8), (r"هيكل", 8),
        (r"شروط\s+العقد", 8),
    ],
    "workflow": [
        (r"\betapes?\b", 10), (r"\bprocedure\b", 10),
        (r"\bdemarche", 10), (r"\bmarche\s+a\s+suivre", 10),
        (r"\bque\s+faire", 10), (r"\bquoi\s+faire", 10),
        (r"\bque\s+dois[- ]je\s+faire", 12),
        (r"\bpublier\b", 8), (r"\bpublication\b", 6),
        (r"\brenouvel", 8),
        (r"\bresili", 8),
        (r"\bexpuls", 8),
        (r"\bimpay", 8),
        (r"\bsous[- ]location\b", 8),
        (r"\bimmatricul", 8),
        (r"\benregistr", 8),
        (r"\binscription\b", 6), (r"\bdeclar", 6),
        (r"\bqu'est-ce\s+que\s+j'ai", 10),
        (r"\bquest-ce\s+que\s+jai", 10),
        (r"\bdepuis\s+\d+\s+an", 8),
        (r"\bj'ai\s+un\s+bail", 8),
        (r"\bjai\s+un\s+bail", 8),
        (r"\bquels?\s+sont\s+mes\s+droits", 8),
        (r"\bmon\s+locataire\b", 6),
        (r"\bdiagramme\b", 12),
        (r"\bschema\b", 12),
        (r"\bvisualis", 10),
        (r"\bmontre[- ]moi\s+les\s+etapes", 14),
        (r"\bmontre\s+(le|les)\s+(etapes|diagramme|schema)", 14),
        (r"\baffiche\s+(le|les)\s+(etapes|diagramme|schema)", 14),
        (r"\bles\s+etapes\s+a\s+suivre", 12),
        (r"كيفاش", 10), (r"كيف\b", 8), (r"كيفيه", 8),
        (r"مراحل", 10), (r"مرحله", 10),
        (r"اجراءات", 10), (r"اجراء", 8),
        (r"خطوات", 10), (r"خطوه", 10),
        (r"ما\s*هي", 6), (r"شنعمل", 10), (r"شنوا", 6),
        (r"ماذا\s*افعل", 10), (r"وقاش", 6),
        (r"تجديد", 8), (r"فسخ", 8), (r"طرد", 8), (r"اخلاء", 8),
        (r"تسجيل", 8),
        (r"ارني\s+المراحل", 14),
        (r"ارني\s+الخطوات", 14),
        (r"اعرض\s+المراحل", 14),
        (r"اعرض\s+الخطوات", 14),
        (r"مخطط", 12),
        (r"رسم\s+بياني", 12),
    ],
}

_INTENT_THRESHOLD = 8


def _detect_intent_keywords(question: str) -> tuple[str | None, dict]:
    q = _normalize(question)
    scores = {k: 0 for k in _INTENT_PATTERNS}
    for intent, patterns in _INTENT_PATTERNS.items():
        for pat, weight in patterns:
            if re.search(pat, q):
                scores[intent] += weight

    best = max(scores, key=scores.get)
    best_score = scores[best]
    ranked = sorted(scores.values(), reverse=True)

    if best_score < _INTENT_THRESHOLD:
        return None, scores
    if len(ranked) >= 2 and ranked[0] == ranked[1]:
        return None, scores
    return best, scores


# ─────────────────────────────────────────────────────────────────
#  HARD WORKFLOW TRIGGERS — must be a REQUEST PHRASE, not a bare noun.
# ─────────────────────────────────────────────────────────────────

_HARD_WORKFLOW = [
    r"\b(veux|voudrais|souhaite|peux[- ]tu|peux[- ]vous)\s+(voir|afficher|montrer|donner)\b",
    r"\b(montre|affiche|donne)[- ]?(moi|nous)?\s+(le|la|les|un|une|des)?\s*(diagramme|schema|etapes?|procedure|demarches?|processus|workflow)",
    r"\b(montre|affiche|donne)[- ]?(moi|nous)?\s+(les\s+)?(etapes?|demarches?)",
    r"\b(voir|afficher)\s+(le|la|les)\s+(diagramme|schema|etapes?)",
    r"\bje\s+veux\s+(voir\s+)?(le|la|les|un|une)?\s*(diagramme|schema|etapes?|processus)",
    r"\bdonne[- ]moi\s+les\s+etapes",
    r"ارني\s+(المراحل|الخطوات)",
    r"اعرض\s+(المراحل|الخطوات)",
    r"اريد\s+(ان\s+ارى\s+)?(المخطط|المراحل|الخطوات)",
    r"ممكن\s+(تشوفني|تعرضلي|تعطيني)\s+(المخطط|المراحل|الخطوات)",
]


# ─────────────────────────────────────────────────────────────────
#  DETERMINISTIC REGION DETECTOR — no LLM
# ─────────────────────────────────────────────────────────────────

_TN_REGIONS_LATIN = {
    "tunis": "تونس",
    "ariana": "أريانة", "l'ariana": "أريانة",
    "ben arous": "بن عروس", "benarous": "بن عروس",
    "manouba": "منوبة", "la manouba": "منوبة",
    "nabeul": "نابل",
    "zaghouan": "زغوان", "zaghouane": "زغوان",
    "bizerte": "بنزرت",
    "beja": "باجة", "béja": "باجة",
    "jendouba": "جندوبة",
    "kef": "الكاف", "le kef": "الكاف",
    "siliana": "سليانة",
    "kairouan": "القيروان",
    "kasserine": "القصرين",
    "sidi bouzid": "سيدي بوزيد", "sidi bou zid": "سيدي بوزيد",
    "sousse": "سوسة", "soussa": "سوسة",
    "monastir": "المنستير",
    "mahdia": "المهدية",
    "sfax": "صفاقس",
    "gafsa": "قفصة",
    "tozeur": "توزر",
    "kebili": "قبلي",
    "gabes": "قابس", "gabès": "قابس",
    "medenine": "مدنين",
    "tataouine": "تطاوين",
}

_TN_REGIONS_AR = [
    "تونس", "أريانة", "اريانة", "بن عروس", "منوبة", "نابل", "زغوان",
    "بنزرت", "باجة", "جندوبة", "الكاف", "سليانة", "القيروان", "القصرين",
    "سيدي بوزيد", "سوسة", "المنستير", "المهدية", "صفاقس", "قفصة",
    "توزر", "قبلي", "قابس", "مدنين", "تطاوين",
]


def _detect_region_deterministic(text: str) -> str | None:
    """Scan the message for a Tunisian region. Returns Arabic form or None."""
    if not text:
        return None

    # Arabic regions first (more precise)
    for ar in _TN_REGIONS_AR:
        if ar in text:
            return ar

    # Latin — accent-insensitive, longest match first
    low = _strip_accents(text.lower())
    for latin, arabic in sorted(_TN_REGIONS_LATIN.items(), key=lambda x: -len(x[0])):
        latin_s = _strip_accents(latin)
        if re.search(r"\b" + re.escape(latin_s) + r"\b", low):
            return arabic

    return None


# ─────────────────────────────────────────────────────────────────
#  DETERMINISTIC LAWYER REQUEST DETECTOR — no LLM
# ─────────────────────────────────────────────────────────────────

_LAWYER_WORD = re.compile(r"\bavocat|\bavocate|محامي|محاميه|محام", re.IGNORECASE)

_LAWYER_DENIALS = [
    r"mon\s+avocat\s+m['a]",
    r"l[']avocat\s+du\s+bailleur",
    r"l[']avocat\s+du\s+locataire",
    r"j[']ai\s+déjà\s+un\s+avocat",
    r"jai\s+deja\s+un\s+avocat",
    r"c[']est\s+quoi\s+le\s+r[oô]le\s+d[']un\s+avocat",
    r"quel\s+est\s+le\s+r[oô]le\s+d[']un\s+avocat",
    r"les\s+avocats\s+sont\s+chers",
    r"je\s+suis\s+avocat",
]


def _looks_like_lawyer_request(text: str) -> bool:
    """
    True when the user is asking US to find/recommend a lawyer.
    False for statements ABOUT a lawyer, definitions, past conversations.
    """
    if not text:
        return False
    if not _LAWYER_WORD.search(text):
        return False

    low = _normalize(text)
    for pat in _LAWYER_DENIALS:
        if re.search(pat, low):
            return False
    return True


# ─────────────────────────────────────────────────────────────────
#  LLM LAWYER CLASSIFIER — fallback only (no "avocat" word present)
# ─────────────────────────────────────────────────────────────────

_LLM_LAWYER_CLASSIFY_PROMPT = """You decide whether the user wants YOU to find or recommend a lawyer.

Return ONLY a JSON object with these 3 keys:

{{
  "intent":   "lawyers" | "none",
  "region":   "<Tunisian governorate in Arabic, or null>",
  "language": "fr" | "ar"
}}

## When to pick "lawyers"

Pick "lawyers" ONLY when the user clearly wants you to produce
a list, a name, or recommendations of lawyers.

✅ "je cherche quelqu'un pour m'aider sur mon bail"
✅ "qui peut me défendre devant le tribunal ?"
✅ "j'ai besoin d'assistance juridique"
✅ "ابحث عن مساعدة قانونية"

## When to pick "none"

Pick "none" for everything else. Especially:
❌ "mon avocat m'a dit que le bail est nul"        (describing a conversation)
❌ "est-ce que je dois consulter un avocat ?"       (asking a legal opinion)
❌ "c'est quoi le rôle d'un avocat ?"               (definition)
❌ "les avocats sont chers"                         (statement)
❌ "merci" / "bonjour" / "ok"                       (small talk)

When in doubt, choose "none".

## Region extraction

If the message contains a Tunisian governorate, return it in Arabic.
Otherwise return null (JSON null, not the string "null").

## Language

If the message contains Arabic characters → "ar". Otherwise → "fr".

## Output

Return ONLY the JSON. No markdown. No prose. No code fences.

Message: "{question}"
"""


def _classify_lawyer_intent(question: str) -> dict:
    """Fallback LLM classifier for ambiguous lawyer requests."""
    try:
        out = _call_llm(
            [{"role": "user", "content": _LLM_LAWYER_CLASSIFY_PROMPT.format(question=question)}],
            model=LLM_FAST_MODEL,
            temperature=0.0,
            max_tokens=80,
        )
        data = _extract_json_object(out) or {}

        intent = str(data.get("intent", "none")).lower().strip()
        if intent not in ("lawyers", "none"):
            intent = "none"

        region = data.get("region")
        if not isinstance(region, str):
            region = None
        else:
            region = region.strip()
            if region.lower() in ("none", "null", ""):
                region = None

        return {"intent": intent, "region": region}
    except Exception as e:
        print(f"⚠️  lawyer classifier failed: {str(e)[:120]}")
        return {"intent": "none", "region": None}


# ─────────────────────────────────────────────────────────────────
#  UNIFIED ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def _detect_intent_with_region(question: str) -> tuple[str, str | None]:
    """
    Returns (intent, region_hint).

    Routing (deterministic first, LLM only for truly ambiguous cases):
      1. Hard workflow triggers      → workflow
      2. Keyword scoring             → workflow | format_contract
      3. Deterministic lawyer check  → lawyers (with region from Python)
      4. LLM classifier fallback     → lawyers (edge cases without the word "avocat")
    """
    if not _HAS_TOOLS:
        return "none", None

    # ── 1. Hard workflow triggers ──
    q_norm = _normalize(question)
    for pat in _HARD_WORKFLOW:
        if re.search(pat, q_norm):
            return "workflow", None

    # ── 2. Keyword scoring for workflow + format_contract ──
    kw_intent, _scores = _detect_intent_keywords(question)
    if kw_intent:
        return kw_intent, None

    # ── 3. Deterministic lawyer detection ──
    region = _detect_region_deterministic(question)
    if _looks_like_lawyer_request(question):
        return "lawyers", region

    # ── 4. LLM fallback for ambiguous cases (no "avocat" word present) ──
    lawyer = _classify_lawyer_intent(question)
    if lawyer["intent"] == "lawyers":
        return "lawyers", region or lawyer["region"]

    return "none", None


def _detect_intent(question: str) -> str:
    """Backwards-compatible string-only version."""
    intent, _region = _detect_intent_with_region(question)
    return intent


# ═══════════════════════════════════════════════════════════════════
#  WORKFLOW ANSWER — Python builds the frame, LLM writes intro/outro
# ═══════════════════════════════════════════════════════════════════

_WORKFLOW_IO_PROMPT = """You write ONLY two short paragraphs in {lang_name}.

The procedure steps are ALREADY displayed to the user below your text.
You must NOT list, repeat, or re-frame the steps.

## Context
Actor: {actor}
User question: {question}

## The procedure covers these steps (for your context only — do NOT repeat)
{steps_summary}

## Output a JSON object with EXACTLY two keys:
{{
  "intro": "ONE sentence acknowledging the user's situation and what this procedure achieves for them. Warm, direct, second person. No bullet, no numbering.",
  "outro": "1-2 sentences. First, which step to start with TODAY and why. Then ONE gentle follow-up question inviting the user to clarify or go deeper. Never end flatly."
}}

Rules:
- Output ONLY the JSON object.
- No markdown, no code fences, no prose outside the JSON.
- Write in {lang_name}.
"""


def _compose_workflow_answer(steps, frame, question, actor, lang) -> str:
    lang_name = "French" if lang == "fr" else "Arabic"

    steps_summary = "\n".join(
        f"- {s['title']}: {s['action']}" for s in steps if s.get("title")
    )

    prompt = _WORKFLOW_IO_PROMPT.format(
        lang_name=lang_name,
        actor=actor,
        question=question,
        steps_summary=steps_summary or "(no steps)",
    )

    intro, outro = "", ""
    try:
        out = _call_llm(
            [{"role": "user", "content": prompt}],
            model=LLM_PRIMARY_MODEL,
            temperature=0.3,
            max_tokens=400,
        )
        data = _extract_json_object(out)
        if data:
            intro = str(data.get("intro", "")).strip()
            outro = str(data.get("outro", "")).strip()
    except Exception as e:
        print(f"⚠️  workflow intro/outro failed: {str(e)[:120]}")

    articles = sorted({
        s.get("article", "").strip()
        for s in steps if s.get("article", "").strip()
    })

    parts = []
    if intro:
        parts.append(intro)
    parts.append(frame)
    if articles:
        prefix = "Fondement : " if lang == "fr" else "الفصول المعتمدة : "
        parts.append(prefix + ", ".join(articles))
    if outro:
        parts.append(outro)

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC PHASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def intro() -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            "[PHASE = INTRO]\n"
            "Produce the intro now. French only. No markdown bold, no **, "
            "no * italics, no numbered list, no actor names listed. "
            "Just greet and ask the user to pick their role using the "
            "buttons below. Do NOT answer any legal question."
        )},
    ]
    answer = _clean(_call_llm(messages))

    choices = [
        {
            "id": "bailleur",
            "label_fr": ACTOR_LABELS["bailleur"]["label_fr"],
            "label_ar": ACTOR_LABELS["bailleur"]["label_ar"],
            "desc_fr": ACTOR_LABELS["bailleur"]["desc_fr"],
            "desc_ar": ACTOR_LABELS["bailleur"]["desc_ar"],
        },
        {
            "id": "commercant",
            "label_fr": ACTOR_LABELS["commercant"]["label_fr"],
            "label_ar": ACTOR_LABELS["commercant"]["label_ar"],
            "desc_fr": ACTOR_LABELS["commercant"]["desc_fr"],
            "desc_ar": ACTOR_LABELS["commercant"]["desc_ar"],
        },
    ]
    return {
        "answer": answer,
        "phase": "intro",
        "actor": None,
        "lang": "fr",
        "choices": choices,
        "sources": [],
        "tool": None,
    }


def choose_actor(actor: str, history: list | None = None, lang: str | None = None) -> dict:
    actor = (actor or "").strip().lower()
    if actor not in ACTOR_LABELS:
        raise ValueError(f"Unknown actor: {actor!r}")

    label = ACTOR_LABELS[actor]
    history = _compress_history(history or [], keep_last=2)
    detected_lang = lang or "fr"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": (
            f"[PHASE = CONFIRM]\n"
            f"The user has selected the role: {actor} "
            f"({label['label_fr']} / {label['label_ar']}).\n"
            f"Acknowledge warmly in ONE short sentence (French by default). "
            f"Then invite them to describe their situation, giving 3–4 short "
            f"French examples (renewal, refusal, non-payment, subletting, deadlines). "
            f"No markdown bold, no **. Do NOT answer any legal question."
        )},
    ]
    answer = _clean(_call_llm(messages))

    return {
        "answer": answer,
        "phase": "actor",
        "actor": actor,
        "lang": detected_lang,
        "choices": [],
        "sources": [],
        "tool": None,
    }


def discuss(
    question: str,
    actor: str,
    history: list | None = None,
    lang: str | None = None,
    k: int = 8,
) -> dict:
    actor = (actor or "").strip().lower()
    if actor not in ACTOR_LABELS:
        raise ValueError(f"Unknown actor: {actor!r}")

    history = _compress_history(history or [], keep_last=2)

    q = (question or "").strip()
    if not q:
        raise ValueError("Empty question.")

    detected_lang = lang or _detect_lang_smart(q)

    # ── Retrieval ──
    retrieved = rag.query(q, k=k, lang=detected_lang)
    parts = []
    for i, r in enumerate(retrieved, 1):
        m = r["metadata"]
        parts.append(
            f"--- Source {i} ---\n"
            f"Article: {m['article']} ({m['titre_fr']} / {m['titre_ar']})\n"
            f"Law: {m['law']}  |  section: {m['section']}  |  lang: {m['lang']}\n"
            f"Text:\n{r['text']}\n"
        )
    context = "\n".join(parts) if parts else "(no relevant articles found)"

    # ── Intent + region ──
    tool_payload = None
    prebuilt_answer = None
    intent, region_hint = _detect_intent_with_region(q)
    print(f"🧠 intent={intent!r}  region={region_hint!r}  q={q!r}")

    # ── WORKFLOW: Python builds the frame; LLM only writes intro/outro ──
    if intent == "workflow" and _HAS_TOOLS:
        try:
            raw_steps = _tools.generate_workflow_steps(
                q, context, actor, detected_lang, _call_llm,
            )
            if raw_steps:
                verified = _tools.verify_workflow_steps(raw_steps, retrieved)
                if len(verified) >= 2:
                    frame = _tools.build_ascii_frame(verified, lang=detected_lang)
                    tool_payload = {
                        "type": "workflow",
                        "steps": verified,
                        "frame": frame,
                    }
                    prebuilt_answer = _compose_workflow_answer(
                        verified, frame, q, actor, detected_lang,
                    )
                else:
                    print(
                        f"⚠️  workflow rejected: only {len(verified)} verified "
                        f"step(s) out of {len(raw_steps)} — falling back to plain answer"
                    )
        except Exception as e:
            print(f"⚠️  workflow tool failed: {str(e)[:140]}")

    # ── LAWYERS: deterministic detection already decided; region is Python-extracted ──
    elif intent == "lawyers" and _HAS_TOOLS:
        try:
            tool_payload = _tools.find_lawyers(
                q,
                _call_llm,
                user_region=region_hint,
                skip_extraction=True,
            )
            print(f"👨‍⚖️ lawyer tool → count={tool_payload.get('count')} region={tool_payload.get('region_detected')!r}")
        except Exception as e:
            print(f"⚠️  lawyer tool failed: {str(e)[:120]}")

    # ── CONTRACT FORMAT ──
    elif intent == "format_contract" and _HAS_TOOLS:
        try:
            tool_payload = _tools.generate_contract_format(
                q, detected_lang, actor, _call_llm,
            )
        except Exception as e:
            print(f"⚠️  format_contract tool failed: {str(e)[:140]}")

    # ── Workflow prebuilt answer short-circuit ──
    if prebuilt_answer:
        return {
            "answer": prebuilt_answer,
            "phase": "discussion",
            "actor": actor,
            "lang": detected_lang,
            "choices": [],
            "sources": [
                {
                    "id": r["id"],
                    "article": r["metadata"]["article"],
                    "title_fr": r["metadata"]["titre_fr"],
                    "title_ar": r["metadata"]["titre_ar"],
                    "law": r["metadata"]["law"],
                    "section": r["metadata"]["section"],
                    "lang": r["metadata"]["lang"],
                    "distance": r.get("distance"),
                }
                for r in retrieved
            ],
            "tool": tool_payload,
        }

    # ── Actor hint ──
    if actor == "bailleur":
        actor_hint = (
            "\n## User identity\n"
            "The user is a property owner (bailleur / المكري).\n"
            "Frame the answer from the owner's perspective: protecting the property, "
            "getting rent on time, keeping the right tenant, avoiding legal traps.\n"
        )
    else:
        actor_hint = (
            "\n## User identity\n"
            "The user is a merchant / tenant (commerçant / التاجر).\n"
            "Frame the answer from the tenant's perspective: protecting the fonds de commerce, "
            "keeping the clientele, negotiating renewal, avoiding eviction.\n"
        )

    # ── Tool note for lawyers / contract ──
    tool_note = ""
    if tool_payload and tool_payload.get("type") == "lawyers":
        region = tool_payload.get("region_detected")
        count = tool_payload.get("count", 0)
        if region:
            tool_note = (
                f"\n## Tool executed: LAWYERS (region detected: {region}, {count} lawyers)\n"
                "Cards are shown below your answer.\n"
                "Move 1: acknowledge you found suitable lawyers in that region.\n"
                "Move 2: explain WHAT to prepare before contacting them "
                "(documents, timeline, questions to ask).\n"
                "Move 3: invite them to look at the cards and contact 2–3 of them.\n"
                "Do NOT list the lawyer names again.\n"
            )
        else:
            tool_note = (
                f"\n## Tool executed: LAWYERS (no region — generic list of {count} lawyers)\n"
                "Cards are shown below your answer.\n"
                "Move 1: acknowledge that you found lawyers that can help.\n"
                "Move 2: tell them what to prepare before contacting a lawyer "
                "(documents, questions to ask).\n"
                "Move 3: invite them to look at the cards. Add ONE short sentence: "
                "'Si vous me précisez votre ville, je peux affiner la liste.' "
                "Do NOT block on the city — the cards are already useful.\n"
                "Do NOT list the lawyer names again.\n"
            )

    elif tool_payload and tool_payload.get("type") == "contract_format":
        tool_note = (
            "\n## Tool executed: CONTRACT SKELETON\n"
            "A structured contract skeleton is shown below your answer.\n"
            "Move 1: acknowledge the type of contract they're working on.\n"
            "Move 2: give 1–2 practical drafting or negotiation tips "
            "(what's often missing, what protects them).\n"
            "Move 3: suggest a next action (contact an avocat, gather documents, etc.).\n"
            "Do NOT repeat the skeleton in your text.\n"
        )

    user_message = (
        f"[PHASE = DISCUSSION]\n"
        f"{actor_hint}\n"
        f"{tool_note}\n"
        f"## Retrieved legal context\n{context}\n\n"
        f"## User question\n{q}\n"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_message},
    ]
    answer = _clean(_call_llm(messages, max_tokens=1800))

    return {
        "answer": answer,
        "phase": "discussion",
        "actor": actor,
        "lang": detected_lang,
        "choices": [],
        "sources": [
            {
                "id": r["id"],
                "article": r["metadata"]["article"],
                "title_fr": r["metadata"]["titre_fr"],
                "title_ar": r["metadata"]["titre_ar"],
                "law": r["metadata"]["law"],
                "section": r["metadata"]["section"],
                "lang": r["metadata"]["lang"],
                "distance": r.get("distance"),
            }
            for r in retrieved
        ],
        "tool": tool_payload,
    }


# ═══════════════════════════════════════════════════════════════════
#  VOICE
# ═══════════════════════════════════════════════════════════════════

def ask_voice(
    audio_path: str,
    actor: str,
    history: list | None = None,
    speak: bool = False,
) -> dict:
    if not _HAS_VOICE:
        raise RuntimeError("Voice module not available (check features/ai/voice.py).")
    return _voice.voice_answer(
        audio_path,
        actor=actor,
        history=history or [],
        speak=speak,
    )


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

SAMPLES = [
    ("bailleur",   "Puis-je refuser de renouveler le bail de mon locataire ?"),
    ("commercant", "Quelles sont les étapes pour publier un contrat de gérance libre ?"),
    ("bailleur",   "Je cherche un avocat à Tunis pour un bail commercial"),
    ("commercant", "Comment rédiger un contrat de gérance libre ? Quelles clauses ?"),
    ("commercant", "J'ai un bail sur un café depuis 2 ans, qu'est-ce que j'ai maintenant ?"),
    ("bailleur",   "هل يمكنني رفض تجديد الكراء؟"),
]


def _pretty(r: dict):
    print(f"\n📍 phase={r['phase']}   👤 actor={r['actor']}   🌍 lang={r['lang']}")
    if r.get("choices"):
        print("🎛️  Choices:")
        for c in r["choices"]:
            print(f"   • [{c['id']}] {c['label_fr']} / {c['label_ar']}")
    if r.get("tool"):
        t = r["tool"]
        print(f"🛠  tool = {t.get('type')}")
        if t.get("type") == "lawyers":
            print(f"   region={t.get('region_detected')}  count={t.get('count')}")
            for it in t.get("items", [])[:5]:
                print(f"   • {it.get('full_name')} ({it.get('region')}) — {it.get('phones')}")
        if t.get("type") == "workflow":
            print(f"   verified steps = {len(t.get('steps', []))}")
            for s in t.get("steps", []):
                print(f"   {s['num']}. {s['title']}  [{s.get('deadline','')}]  {s.get('article','')}")
        if t.get("type") == "contract_format":
            print(f"   contract_type = {t.get('contract_type')}")
            print(f"   title = {t.get('title')}")
            for sec in t.get("sections", []):
                print(f"   § {sec['num']}. {sec['title']}  ({len(sec['items'])} items)")
    if r.get("sources"):
        print(f"📚 Sources ({len(r['sources'])}):")
        for s in r["sources"]:
            print(f"   • {s['article']:<20} [{s['section']:<12}] {s['title_fr']}")
    print(f"\n💬 {r['answer']}")


def _run_cli():
    args = sys.argv[1:]

    if args and args[0] == "--intro":
        print("\n🎬 PHASE 1 — INTRO")
        _pretty(intro())
        return

    if args and args[0] == "--actor":
        actor = args[1] if len(args) > 1 else "bailleur"
        fake_history = [{"role": "assistant", "content": "(previous: Dalil intro)"}]
        print(f"\n🎬 PHASE 2 — CONFIRM (actor={actor})")
        _pretty(choose_actor(actor, fake_history))
        return

    if args and args[0] == "--discuss":
        if "--actor" not in args:
            print("Usage: python -m features.ai.agent --discuss '<question>' --actor <bailleur|commercant>")
            return
        ai = args.index("--actor")
        actor = args[ai + 1]
        question = " ".join(args[1:ai])
        fake_history = [
            {"role": "assistant", "content": "(previous: Dalil intro)"},
            {"role": "user",      "content": actor},
            {"role": "assistant", "content": "(previous: Dalil acknowledged)"},
        ]
        print(f"\n🎬 PHASE 3 — DISCUSSION (actor={actor})")
        _pretty(discuss(question, actor=actor, history=fake_history))
        return

    if args and args[0] == "--voice":
        if "--actor" not in args:
            print("Usage: python -m features.ai.agent --voice <audio> --actor <bailleur|commercant> [--speak]")
            return
        ai = args.index("--actor")
        actor = args[ai + 1]
        audio = args[1] if args[1] != "--actor" else args[ai + 2]
        r = ask_voice(audio, actor=actor, speak="--speak" in args)
        print(f"\n❓ {r.get('question', '')}")
        _pretty(r)
        return

    print("\n" + "═" * 78)
    print("  Dalil · Feature 2 — Workflow Guidance (conversational)")
    print("═" * 78)
    for actor, q in SAMPLES:
        print("\n" + "─" * 78)
        print(f"❓ [{actor}] {q}\n" + "─" * 78)
        fake_history = [
            {"role": "assistant", "content": "(previous: Dalil intro)"},
            {"role": "user",      "content": actor},
            {"role": "assistant", "content": "(previous: Dalil acknowledged)"},
        ]
        _pretty(discuss(q, actor=actor, history=fake_history))


if __name__ == "__main__":
    _run_cli()