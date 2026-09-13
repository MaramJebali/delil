"""
Tools for the Feature 2 agent.

- find_lawyers()                 → top N lawyers by region (advocates.json)
- generate_workflow_steps()      → LLM → structured steps JSON
- verify_workflow_steps()        → verify each step against the retrieved vector-DB chunks
- build_ascii_frame()            → verified steps → ASCII frame (deterministic)
- generate_contract_format()     → contract skeleton from contract_requirements.json

Note: mermaid / Kroki rendering has been removed — the ASCII frame is the diagram.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════════

AI_DIR       = Path(__file__).resolve().parent
DATA_DIR     = AI_DIR / "data"
AVOCATS_PATH = DATA_DIR / "advocates.json"
REQUIREMENTS_PATH = DATA_DIR / "contract_requirements.json"

if not AVOCATS_PATH.exists():
    _alt = DATA_DIR / "avocats.json"
    if _alt.exists():
        AVOCATS_PATH = _alt


# ═══════════════════════════════════════════════════════════════════
#  FRENCHISM SCRUBBER — safety net if the LLM still emits French terms
# ═══════════════════════════════════════════════════════════════════

_BANNED_MAP = {
    r"\bBODACC\b":                       "JORT",
    r"\bKbis\b":                         "Extrait RNE",
    r"\bINPI\b":                         "INNORPI",
    r"\bRCS\b":                          "RNE",
    r"registre\s+du\s+commerce":         "RNE",
    r"greffe\s+du\s+tribunal\s+de\s+commerce":
                                         "greffe du Tribunal de Première Instance",
    r"\btribunal\s+de\s+commerce\b":     "Tribunal de Première Instance",
}


def _scrub_frenchism(text: str) -> str:
    if not text:
        return text
    for pat, repl in _BANNED_MAP.items():
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


# ═══════════════════════════════════════════════════════════════════
#  LAWYER FINDER
# ═══════════════════════════════════════════════════════════════════

def _load_avocats() -> list[dict]:
    """
    Handle the actual advocates.json shape:
      { "advocates": { "all_regions": [ {...}, ... ] } }
    Also supports legacy shapes: top-level list, {"avocats": [...]}, {"lawyers": [...]}.
    """
    if not AVOCATS_PATH.exists():
        print(f"⚠️  Missing lawyers file: {AVOCATS_PATH}")
        return []
    with open(AVOCATS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        adv = data.get("advocates")
        if isinstance(adv, dict):
            return adv.get("all_regions", []) or []
        if isinstance(adv, list):
            return adv
        return data.get("avocats", data.get("lawyers", [])) or []
    if isinstance(data, list):
        return data
    return []


def _extract_region_from_query(query: str, llm_fn) -> str | None:
    """
    Fallback: ask the LLM to extract a Tunisian region when the caller
    did not provide one. Not used when `skip_extraction=True`.
    """
    prompt = (
        "Extract the Tunisian city or region mentioned in this message.\n"
        "Reply with the region name in ARABIC (e.g. تونس, صفاقس, سوسة, أريانة, نابل).\n"
        "If no location is mentioned, reply with NONE.\n"
        "Reply with ONLY the name, nothing else.\n\n"
        f'Message: "{query}"'
    )
    try:
        out = llm_fn([{"role": "user", "content": prompt}],
                     temperature=0.0, max_tokens=20)
        out = out.strip().strip('"').strip()
        if out.upper().startswith("NONE") or len(out) < 2 or len(out) > 40:
            return None
        return out
    except Exception:
        return None


def find_lawyers(
    query: str,
    llm_fn,
    user_region: str | None = None,
    limit: int = 5,
    skip_extraction: bool = False,
) -> dict:
    """
    Find top N lawyers by region.

    `user_region`: pre-resolved region (Arabic), or None.
    `skip_extraction`: when True, do NOT call the LLM to extract a region —
        trust `user_region` as-is (may be None). Used when the caller
        (e.g. agent._classify_lawyer_intent) already extracted the region.
    """
    lawyers = _load_avocats()
    if not lawyers:
        return {"type": "lawyers", "items": [], "note": "Base d'avocats indisponible."}

    if skip_extraction:
        region = user_region
    else:
        region = user_region or _extract_region_from_query(query, llm_fn)

    scored = []
    for l in lawyers:
        score = 0
        reasons = []
        l_region  = (l.get("region") or "").strip()
        l_court   = (l.get("primary_court") or "").strip()
        l_tableau = (l.get("tableau") or "").strip()

        if region:
            if region in l_region or l_region in region:
                score += 100
                reasons.append(f"Basé à {l_region}")
            if region in l_court or l_court in region:
                score += 60
                reasons.append(f"Pratique devant le tribunal de {l_court}")

        if "تعقيب" in l_tableau:
            score += 20
            reasons.append("Spécialisé en représentation commerciale")

        scored.append({"lawyer": l, "score": score, "reasons": reasons})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:limit]

    items = []
    for entry in top:
        l = entry["lawyer"]
        address = l.get("address") or ""
        items.append({
            "id": l.get("id"),
            "full_name": l.get("full_name"),
            "address": address,
            "phones": l.get("phone_numbers", []),
            "court": l.get("primary_court"),
            "region": l.get("region"),
            "tableau": l.get("tableau"),
            "reasons": entry["reasons"],
            "maps_url": "https://www.google.com/maps/search/?api=1&query="
                        + address.replace(" ", "+"),
        })

    return {
        "type": "lawyers",
        "region_detected": region,
        "count": len(items),
        "items": items,
    }


# ═══════════════════════════════════════════════════════════════════
#  WORKFLOW STEPS (LLM → JSON)
# ═══════════════════════════════════════════════════════════════════

def _extract_json_array(text: str) -> list | None:
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    m = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    start = text.find("[")
    end   = text.rfind("]")
    if start != -1 and end > start:
        chunk = text[start:end + 1]
        chunk = re.sub(r",\s*([\]}])", r"\1", chunk)
        try:
            data = json.loads(chunk)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return None


def _build_workflow_prompt(question: str, retrieved_context: str, actor: str, lang: str) -> str:
    lang_rule = "Write all titles and actions in FRENCH." if lang == "fr" \
                else "Write all titles and actions in ARABIC."
    return f"""You build the step-by-step procedure for a TUNISIAN legal question.

═══════════════════════════════════════════════════════════
WHAT TO OUTPUT
═══════════════════════════════════════════════════════════
A JSON array of 4 to 6 steps, chronological order.
Each step is an object with EXACTLY these 6 keys:

{{
  "num": 1,
  "title": "verb + object, max 55 chars. Example: 'Déposer la demande au RNE'",
  "action": "one sentence: who does what, where, with which document. Max 180 chars.",
  "deadline": "legal delay if the article states one, else \\"\\"",
  "authority": "RNE | JORT | Greffe du Tribunal de Première Instance | Huissier | Tribunal — or \\"\\"",
  "article": "Article X du Code de Commerce or Article Y de la loi 77-37 — or \\"\\""
}}

═══════════════════════════════════════════════════════════
RULES — FOLLOW EXACTLY
═══════════════════════════════════════════════════════════
1. {lang_rule}
2. Use ONLY articles present in the CONTEXT below.
   Every step MUST have an "article" field that matches an article in the context.
   If you cannot find a matching article, DO NOT invent — leave it empty.
3. If a step has no deadline in the context, leave "deadline" empty. Never guess.
4. First step = the first action the user takes. Last step = the final result.
5. If the procedure involves registering or publishing a commercial act,
   ALWAYS include a step for "Inscription au RNE".

═══════════════════════════════════════════════════════════
TUNISIAN BODIES — USE THESE, NEVER FRENCH ONES
═══════════════════════════════════════════════════════════
✅ CORRECT: RNE, JORT, Greffe du Tribunal de Première Instance,
            Huissier de justice, Recette des Finances, Municipalité, APC.

❌ FORBIDDEN: BODACC, INPI, Kbis, RCS,
              "registre du commerce" (→ RNE),
              "tribunal de commerce" (→ Tribunal de Première Instance).

═══════════════════════════════════════════════════════════
CONTEXT — retrieved Tunisian legal articles
═══════════════════════════════════════════════════════════
{retrieved_context}

═══════════════════════════════════════════════════════════
ACTOR: {actor}
QUESTION: {question}
═══════════════════════════════════════════════════════════

OUTPUT: return ONLY the raw JSON array. Start with [ and end with ]. No prose.
"""


def _normalize_steps(raw: list) -> list[dict]:
    clean = []
    for i, s in enumerate(raw, 1):
        if not isinstance(s, dict):
            continue
        clean.append({
            "num":       s.get("num", i),
            "title":     _scrub_frenchism(str(s.get("title", "")))[:70],
            "action":    _scrub_frenchism(str(s.get("action", "")))[:240],
            "deadline":  _scrub_frenchism(str(s.get("deadline", "")))[:30],
            "authority": _scrub_frenchism(str(s.get("authority", "")))[:40],
            "article":   _scrub_frenchism(str(s.get("article", "")))[:60],
        })
    return clean


def generate_workflow_steps(
    question: str,
    retrieved_context: str,
    actor: str,
    lang: str,
    llm_fn,
) -> list[dict] | None:
    prompt = _build_workflow_prompt(question, retrieved_context, actor, lang)
    try:
        out = llm_fn([{"role": "user", "content": prompt}],
                     temperature=0.1, max_tokens=1600)
        print(f"\n🔎 RAW LLM OUTPUT (workflow steps):\n{out[:600]}\n")

        raw = _extract_json_array(out)
        if not raw or len(raw) < 2:
            print(f"⚠️  parser got {len(raw) if raw else 0} steps")
            return None

        return _normalize_steps(raw) or None
    except Exception as e:
        print(f"⚠️  workflow steps failed: {type(e).__name__}: {str(e)[:140]}")
    return None


# ═══════════════════════════════════════════════════════════════════
#  VERIFY WORKFLOW STEPS against the retrieved chunks
# ═══════════════════════════════════════════════════════════════════

_VALID_AUTHORITIES = (
    "rne", "registre national", "jort", "journal officiel",
    "greffe", "tribunal", "première instance", "premiere instance",
    "huissier", "recette", "municipalit", "apc",
    "القباضة", "الرائد الرسمي", "كتابة المحكمة", "عدل منفذ",
)


def verify_workflow_steps(steps: list[dict], retrieved: list[dict]) -> list[dict]:
    """
    Keep only steps that are supported by the retrieved chunks.
    - article: must reference an article present in retrieved metadata
    - deadline: if present, its numeric value must appear in a 'delais' chunk
    - authority: if present, must be one of the known Tunisian bodies
    Steps with an unsupported article are DROPPED.
    """
    retrieved_articles = set()
    delais_text_parts = []

    for r in retrieved:
        meta = r.get("metadata", {})
        art = str(meta.get("article", ""))
        for num in re.findall(r"\d+", art):
            retrieved_articles.add(num)

        section = meta.get("section", "")
        if section == "delais":
            delais_text_parts.append(r.get("text", ""))

    delais_text = " ".join(delais_text_parts)

    verified: list[dict] = []
    for s in steps:
        art = str(s.get("article", "")).strip()

        # ── Article check ──
        nums = re.findall(r"\d+", art)
        if not nums or not any(n in retrieved_articles for n in nums):
            continue

        # ── Deadline check ──
        deadline = str(s.get("deadline", "")).strip()
        if deadline:
            dm = re.search(r"\d+", deadline)
            if dm and dm.group(0) not in delais_text:
                deadline = ""

        # ── Authority check ──
        authority = str(s.get("authority", "")).strip()
        if authority:
            low = authority.lower()
            if not any(a in low for a in _VALID_AUTHORITIES):
                authority = ""

        verified.append({
            "num":       s.get("num", len(verified) + 1),
            "title":     s.get("title", ""),
            "action":    s.get("action", ""),
            "deadline":  deadline,
            "authority": authority,
            "article":   art,
        })

    return verified


# ═══════════════════════════════════════════════════════════════════
#  ASCII FRAME (deterministic Python-side rendering)
# ═══════════════════════════════════════════════════════════════════

_CIRCLES = "①②③④⑤⑥⑦⑧⑨⑩"


def _wrap(text: str, width: int = 62) -> list[str]:
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def build_ascii_frame(steps: list[dict], lang: str = "fr") -> str:
    if not steps:
        return ""

    title  = "Étapes de la procédure" if lang == "fr" else "خطوات الإجراء"
    bar_w  = 48
    header = "╭─ " + title + " " + "─" * max(0, bar_w - len(title) - 4) + "╮"
    footer = "╰" + "─" * (bar_w - 2) + "╯"

    lines = [header, "│"]

    for i, s in enumerate(steps):
        circle = _CIRCLES[i] if i < len(_CIRCLES) else f"({i+1})"
        t = (s.get("title") or "").strip()
        a = (s.get("action") or "").strip()

        lines.append(f"│  {circle} {t}")

        for wl in _wrap(a, width=60):
            lines.append(f"│     {wl}")

        meta_bits = []
        if s.get("deadline"):
            prefix = "⏱ Délai : " if lang == "fr" else "⏱ الأجل : "
            meta_bits.append(prefix + s["deadline"])
        if s.get("authority"):
            meta_bits.append("🏛 " + s["authority"])
        if meta_bits:
            lines.append(f"│     {' | '.join(meta_bits)}")

        if i < len(steps) - 1:
            lines.append("│     ↓")

    lines.append("│")
    lines.append(footer)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  CONTRACT FORMAT (from contract_requirements.json)
# ═══════════════════════════════════════════════════════════════════

def _load_contract_requirements() -> dict:
    if not REQUIREMENTS_PATH.exists():
        print(f"⚠️  Missing requirements file: {REQUIREMENTS_PATH}")
        return {}
    with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _match_contract_type(reqs: dict, hint: str) -> tuple[str | None, dict | None]:
    ctypes = reqs.get("contract_types", {})
    if not ctypes:
        return None, None
    h = (hint or "").strip().lower()
    if not h:
        h = "location-gerance"
    for tid, tdata in ctypes.items():
        if tid == h:
            return tid, tdata
    for tid, tdata in ctypes.items():
        aliases = [a.lower() for a in tdata.get("aliases_fr", [])] \
                + [a.lower() for a in tdata.get("aliases_ar", [])]
        if tid in h or h in tid:
            return tid, tdata
        for a in aliases:
            if a and (a in h or h in a):
                return tid, tdata
    if "location-gerance" in ctypes:
        return "location-gerance", ctypes["location-gerance"]
    return None, None


def _detect_contract_type_from_query(query: str, llm_fn) -> str:
    prompt = (
        "Which Tunisian commercial contract type does this message refer to?\n"
        "Reply with ONLY one of these keywords:\n"
        "  location-gerance | bail-commercial | cession-fonds-commerce | none\n\n"
        f'Message: "{query}"'
    )
    try:
        out = llm_fn([{"role": "user", "content": prompt}],
                     temperature=0.0, max_tokens=15)
        out = out.strip().lower()
        for k in ("location-gerance", "bail-commercial", "cession-fonds-commerce"):
            if k in out:
                return k
    except Exception:
        pass
    return "location-gerance"


def generate_contract_format(query: str, lang: str, actor: str, llm_fn) -> dict | None:
    reqs = _load_contract_requirements()
    if not reqs:
        return None

    type_hint = _detect_contract_type_from_query(query, llm_fn)
    matched_id, matched = _match_contract_type(reqs, type_hint)
    if not matched:
        return None

    groups: dict[str, list] = {}
    for item in matched.get("mandatory_items", []):
        g = item.get("group", "other")
        groups.setdefault(g, []).append({
            "label_fr": item.get("label_fr", ""),
            "label_ar": item.get("label_ar", ""),
            "legal_basis": item.get("legal_basis", ""),
            "severity": item.get("severity", "info"),
        })

    post_form = reqs.get("post_signature_formalities", {}).get(matched_id, [])
    post_labels = [f.get("label_fr", "") for f in post_form if f.get("label_fr")]

    lang_rule = "Reply in FRENCH." if lang == "fr" else "Reply in ARABIC."
    prompt = f"""Produce a structured contract skeleton for a Tunisian contract of type: {matched.get('label_fr')}.

Output a JSON object:
{{
  "title": "Contrat de {matched.get('label_fr')}",
  "sections": [
    {{
      "num": 1,
      "title": "Parties",
      "intro": "1 short sentence explaining what this section covers",
      "items": ["Nom et prénom du propriétaire", "CIN / passeport"],
      "legal_basis": "Code de Commerce art. 189 bis"
    }}
  ],
  "post_signature": ["Publication au JORT + 2 journaux dans les 15 jours"]
}}

Rules:
- Use ONLY the items provided below. Do NOT invent.
- Order the sections like a real Tunisian contract.
- Between 4 and 6 sections.
- {lang_rule}
- Output ONLY the JSON object, no prose, no markdown.

Actor: {actor}

Items grouped by section:
{json.dumps(groups, ensure_ascii=False, indent=2)}

Post-signature formalities:
{json.dumps(post_labels, ensure_ascii=False, indent=2)}
"""
    try:
        out = llm_fn([{"role": "user", "content": prompt}],
                     temperature=0.2, max_tokens=2000)
        m = re.search(r"\{.*\}", out, flags=re.DOTALL)
        if not m:
            return None
        fmt = json.loads(m.group(0))

        sections = []
        for i, s in enumerate(fmt.get("sections", []), 1):
            if not isinstance(s, dict):
                continue
            sections.append({
                "num": s.get("num", i),
                "title": str(s.get("title", ""))[:80],
                "intro": str(s.get("intro", ""))[:200],
                "items": [str(x)[:160] for x in (s.get("items") or [])][:20],
                "legal_basis": str(s.get("legal_basis", ""))[:120],
            })

        return {
            "type": "contract_format",
            "contract_type": matched_id,
            "label": matched.get("label_fr"),
            "label_ar": matched.get("label_ar"),
            "title": str(fmt.get("title", f"Contrat de {matched.get('label_fr')}"))[:120],
            "sections": sections,
            "post_signature": [str(x)[:160] for x in (fmt.get("post_signature") or post_labels)][:10],
            "legal_governance": matched.get("legal_governance", []),
        }
    except Exception as e:
        print(f"⚠️  format_contract tool failed: {str(e)[:140]}")
        return None