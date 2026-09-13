"""
t4.py — Test the workflow diagram pipeline end-to-end.

Run from:  C:\\Users\\maram\\Documents\\Delil\\backend
Command:   python t4.py
"""

from features.ai.agent import _detect_intent, _call_llm
from features.ai import rag, tools

# ── The question you want to test ──────────────────────────────
q = "Quelles sont les étapes pour publier un contrat de gérance libre ?"
actor = "commercant"
lang  = "fr"

print("=" * 70)
print(f"QUESTION: {q}")
print(f"ACTOR   : {actor}   LANG: {lang}")
print("=" * 70)

# ── 1) Intent detection ───────────────────────────────────────
intent = _detect_intent(q)
print(f"\n[1] intent = {intent}")
if intent != "workflow":
    print(f"❌ Intent is '{intent}', not 'workflow' → tool won't fire.")
    print("   → Add more keywords to _INTENT_PATTERNS['workflow'] in agent.py")
    raise SystemExit

# ── 2) RAG retrieval ──────────────────────────────────────────
retrieved = rag.query(q, k=6, lang=lang)
print(f"\n[2] retrieved {len(retrieved)} articles:")
for r in retrieved:
    print(f"    - {r['metadata']['article']}")

context = "\n".join(
    f"--- Source {i} ---\n"
    f"Article: {r['metadata']['article']}\n"
    f"{r['text']}\n"
    for i, r in enumerate(retrieved, 1)
)

# ── 3) Generate steps (LLM → JSON) ────────────────────────────
print(f"\n[3] calling generate_workflow_steps()...")
steps = tools.generate_workflow_steps(q, context, actor, lang, _call_llm)

if not steps:
    print("\n❌ BREAKS HERE — generate_workflow_steps returned None.")
    print("   → See the RAW LLM OUTPUT printed above.")
    print("   → Fix = replace generate_workflow_steps in tools.py with the tolerant version.")
    raise SystemExit

print(f"\n✅ got {len(steps)} steps:")
for s in steps:
    print(f"    {s['num']}. {s['title']}  [{s.get('deadline','')}]  {s.get('article','')}")

# ── 4) Steps → Mermaid code ───────────────────────────────────
mermaid = tools.steps_to_mermaid(steps, lang=lang)
print(f"\n[4] mermaid_code:\n{mermaid}")

# ── 5) Mermaid → image URL ────────────────────────────────────
urls = tools.render_mermaid_url(mermaid, fmt="svg")
print(f"\n[5] primary URL  : {urls['primary']}")
print(f"    fallback URL : {urls['fallback']}")
print(f"    URL length   : {len(urls['primary'])} chars")

print("\n" + "=" * 70)
print("✅ PIPELINE OK — copy the primary URL into your browser.")
print("   If the browser shows a diagram, the backend is fine.")
print("   If the browser shows nothing, it's a Kroki/font/rendering issue.")
print("=" * 70)