"""
RAG — vector store for the Dalil legal knowledge base.

Chunking strategy: one chunk per (article × section × language).
Sections:  summary | conditions | consequences | delais | keywords | related
Languages: fr | ar
Chroma location: features/ai/chroma_db/   (next to the agent)
JSONs location:  features/ai/data/loi_77_37.json
                 features/ai/data/code_comm.json

Nothing in the source JSONs is dropped:
  • Text fields (concept, résumé, conditions, conséquences, délais,
    mots-clés, articles_lies) → in the chunk text.
  • Structural fields (acteurs, acteurs_ar, articles_lies, source, objet,
    source_officielle, livre, prolongeable) → in every chunk's metadata.

Commands:
    python -m features.ai.rag build
    python -m features.ai.rag query "<question>"
    python -m features.ai.rag article <article_id>
    python -m features.ai.rag stats
"""

# ── Environment shims (MUST come before any torch / transformers import) ──
import os
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import json
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")

AI_DIR = Path(__file__).resolve().parent
DATA_DIR = AI_DIR / "data"
CHROMA_DIR = AI_DIR / "chroma_db"
COLLECTION_NAME = "dalil_law"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")

# Force CPU for embeddings (avoids CUDA sm_120 crash on RTX 50-series).
# Set EMBEDDING_DEVICE=cuda in .env later, once PyTorch is upgraded to cu128.
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

KB_FILES = {
    "loi_77_37": DATA_DIR / "loi_77_37.json",
    "code_commerce": DATA_DIR / "code_comm.json",
}


# ═══════════════════════════════════════════════════════════════════
#  METADATA
# ═══════════════════════════════════════════════════════════════════

def _root_meta(root: dict) -> dict:
    """File-level metadata (source, objet, JORT, livre…)."""
    return {
        "root_source":               root.get("source", ""),
        "root_source_ar":            root.get("source_arabe", ""),
        "root_objet_fr":             root.get("objet_fr", ""),
        "root_objet_ar":             root.get("objet_ar", ""),
        "root_source_officielle":    root.get("source_officielle", ""),
        "root_source_officielle_ar": root.get("source_officielle_ar", ""),
        "root_livre":                root.get("livre", ""),
        "root_livre_ar":             root.get("livre_arabe", ""),
    }


def _article_meta(law_key: str, art: dict, root_meta: dict) -> dict:
    """Every article-level field that belongs in metadata."""
    return {
        "law":           law_key,
        "article_id":    art["id"],
        "article":       art.get("article", ""),
        "titre_fr":      art.get("titre_fr", ""),
        "titre_ar":      art.get("titre_ar", ""),
        "concept_fr":    art.get("concept_fr", ""),
        "concept_ar":    art.get("concept_ar", ""),
        "acteurs":       ",".join(art.get("acteurs", [])),
        "acteurs_ar":    ",".join(art.get("acteurs_ar", [])),
        "articles_lies": ",".join(art.get("articles_lies", [])),
        **root_meta,
    }


# ═══════════════════════════════════════════════════════════════════
#  CHUNKING
# ═══════════════════════════════════════════════════════════════════

def _split_article(law_key: str, art: dict, root_meta: dict) -> list[dict]:
    base = _article_meta(law_key, art, root_meta)
    chunks: list[dict] = []
    aid = art["id"]
    label = art.get("article", "")

    # ── SUMMARY (titre + concept + résumé) ─────
    chunks.append({
        "id": f"{aid}__summary__fr",
        "text": "\n".join(filter(None, [
            f"[{label}] {art.get('titre_fr', '')}",
            f"Concept : {art.get('concept_fr', '')}" if art.get("concept_fr") else "",
            art.get("resume_fr", ""),
        ])),
        "metadata": {**base, "section": "summary", "lang": "fr"},
    })
    chunks.append({
        "id": f"{aid}__summary__ar",
        "text": "\n".join(filter(None, [
            f"[{label}] {art.get('titre_ar', '')}",
            f"المفهوم : {art.get('concept_ar', '')}" if art.get("concept_ar") else "",
            art.get("resume_ar", ""),
        ])),
        "metadata": {**base, "section": "summary", "lang": "ar"},
    })

    # ── CONDITIONS ─────────────────────────────
    fr = [c.get("texte_fr", "") for c in art.get("conditions", []) if c.get("texte_fr")]
    ar = [c.get("texte_ar", "") for c in art.get("conditions", []) if c.get("texte_ar")]
    if fr:
        chunks.append({
            "id": f"{aid}__conditions__fr",
            "text": f"[{label}] Conditions d'application\n" + "\n".join(f"- {c}" for c in fr),
            "metadata": {**base, "section": "conditions", "lang": "fr"},
        })
    if ar:
        chunks.append({
            "id": f"{aid}__conditions__ar",
            "text": f"[{label}] شروط التطبيق\n" + "\n".join(f"- {c}" for c in ar),
            "metadata": {**base, "section": "conditions", "lang": "ar"},
        })

    # ── CONSEQUENCES ───────────────────────────
    fr = [c.get("texte_fr", "") for c in art.get("consequences", []) if c.get("texte_fr")]
    ar = [c.get("texte_ar", "") for c in art.get("consequences", []) if c.get("texte_ar")]
    if fr:
        chunks.append({
            "id": f"{aid}__consequences__fr",
            "text": f"[{label}] Conséquences\n" + "\n".join(f"- {c}" for c in fr),
            "metadata": {**base, "section": "consequences", "lang": "fr"},
        })
    if ar:
        chunks.append({
            "id": f"{aid}__consequences__ar",
            "text": f"[{label}] النتائج\n" + "\n".join(f"- {c}" for c in ar),
            "metadata": {**base, "section": "consequences", "lang": "ar"},
        })

    # ── DELAIS (with prolongeable) ─────────────
    delais = art.get("delais", [])
    if delais:
        fr_lines, ar_lines = [], []
        for d in delais:
            prol_fr = "prolongeable" if d.get("prolongeable") else "non prolongeable"
            prol_ar = "قابل للتمديد" if d.get("prolongeable") else "غير قابل للتمديد"
            fr_lines.append(
                f"- {d.get('duree', '')} ({prol_fr}) : "
                f"{d.get('evenement_declencheur', '')} → {d.get('consequence', '')}"
            )
            ar_lines.append(
                f"- {d.get('duree_ar', '')} ({prol_ar}) : "
                f"{d.get('evenement_declencheur_ar', '')} → {d.get('consequence_ar', '')}"
            )
        chunks.append({
            "id": f"{aid}__delais__fr",
            "text": f"[{label}] Délais légaux\n" + "\n".join(fr_lines),
            "metadata": {**base, "section": "delais", "lang": "fr"},
        })
        chunks.append({
            "id": f"{aid}__delais__ar",
            "text": f"[{label}] الآجال القانونية\n" + "\n".join(ar_lines),
            "metadata": {**base, "section": "delais", "lang": "ar"},
        })

    # ── KEYWORDS ───────────────────────────────
    kw_fr = art.get("mots_cles_fr", [])
    kw_ar = art.get("mots_cles_ar", [])
    if kw_fr:
        chunks.append({
            "id": f"{aid}__keywords__fr",
            "text": f"[{label}] Mots-clés : " + ", ".join(kw_fr),
            "metadata": {**base, "section": "keywords", "lang": "fr"},
        })
    if kw_ar:
        chunks.append({
            "id": f"{aid}__keywords__ar",
            "text": f"[{label}] كلمات مفتاحية : " + "، ".join(kw_ar),
            "metadata": {**base, "section": "keywords", "lang": "ar"},
        })

    # ── RELATED (articles_lies) ────────────────
    related = art.get("articles_lies", [])
    if related:
        chunks.append({
            "id": f"{aid}__related__fr",
            "text": f"[{label}] Articles liés : " + ", ".join(related),
            "metadata": {**base, "section": "related", "lang": "fr"},
        })
        chunks.append({
            "id": f"{aid}__related__ar",
            "text": f"[{label}] الفصول ذات الصلة : " + "، ".join(related),
            "metadata": {**base, "section": "related", "lang": "ar"},
        })

    return chunks


# ═══════════════════════════════════════════════════════════════════
#  LOAD
# ═══════════════════════════════════════════════════════════════════

def _load_chunks() -> list[dict]:
    all_chunks: list[dict] = []
    for law_key, path in KB_FILES.items():
        if not path.exists():
            print(f"⚠️  Missing: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        root = next(iter(data.values()))
        root_meta = _root_meta(root)
        articles = root.get("articles", [])
        print(f"  📖 {law_key}: {len(articles)} articles ({path.name})")
        for art in articles:
            all_chunks.extend(_split_article(law_key, art, root_meta))
    return all_chunks


# ═══════════════════════════════════════════════════════════════════
#  BUILD
# ═══════════════════════════════════════════════════════════════════

def build():
    import chromadb
    from sentence_transformers import SentenceTransformer

    print("\n🏗️  Building Dalil vector database...\n")
    chunks = _load_chunks()
    if not chunks:
        print("❌ No chunks. Add JSON files to features/ai/data/")
        return

    fr = sum(1 for c in chunks if c["metadata"]["lang"] == "fr")
    ar = sum(1 for c in chunks if c["metadata"]["lang"] == "ar")
    print(f"\n📦 Total chunks: {len(chunks)}  (fr={fr}, ar={ar})")

    sections: dict[str, int] = {}
    for c in chunks:
        s = c["metadata"]["section"]
        sections[s] = sections.get(s, 0) + 1
    print(f"   Sections: {sections}")

    print(f"\n🤖 Loading embedding model: {EMBEDDING_MODEL_NAME} (device={EMBEDDING_DEVICE})")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME, device=EMBEDDING_DEVICE)
    print("✅ Embedder ready")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"🗑️  Removed old collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = ["passage: " + c["text"] for c in chunks]
    print(f"🧮 Embedding {len(texts)} chunks...")
    embeddings = embedder.encode(
        texts,
        show_progress_bar=True,
        batch_size=16,
        normalize_embeddings=True,
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        embeddings=embeddings.tolist(),
    )

    print(f"\n✅ Collection '{COLLECTION_NAME}' built with {len(chunks)} chunks")
    print(f"📂 Stored at: {CHROMA_DIR}")


# ═══════════════════════════════════════════════════════════════════
#  QUERY
# ═══════════════════════════════════════════════════════════════════

_embedder_singleton = None


def _get_embedder():
    global _embedder_singleton
    if _embedder_singleton is None:
        from sentence_transformers import SentenceTransformer
        _embedder_singleton = SentenceTransformer(
            EMBEDDING_MODEL_NAME, device=EMBEDDING_DEVICE
        )
    return _embedder_singleton


def _get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def _detect_lang(text: str) -> str:
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return "ar" if arabic > 3 else "fr"


def query(
    text: str,
    k: int = 6,
    law: Optional[str] = None,
    lang: Optional[str] = None,
    sections: Optional[list[str]] = None,
) -> list[dict]:
    """
    Retrieve top-k chunks for a query.
    - `law`      : restrict to "loi_77_37" or "code_commerce"
    - `lang`     : force "fr" or "ar"
    - `sections` : restrict to e.g. ["summary", "keywords"]
    """
    collection = _get_collection()
    embedder = _get_embedder()

    lang = lang or _detect_lang(text)
    emb = embedder.encode(["query: " + text], normalize_embeddings=True)[0].tolist()

    def _do(where_clause):
        res = collection.query(query_embeddings=[emb], n_results=k, where=where_clause)
        return [
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i] if res.get("distances") else None,
            }
            for i in range(len(res["ids"][0]))
        ]

    conditions: list[dict] = [{"lang": lang}]
    if law:
        conditions.append({"law": law})
    if sections:
        conditions.append({"section": {"$in": sections}})

    where_lang = conditions[0] if len(conditions) == 1 else {"$and": conditions}
    results = _do(where_lang)

    if len(results) < 3:
        fallback = [{"law": law}] if law else None
        results = _do(fallback)

    return results


def get_article_chunks(article_id: str) -> list[dict]:
    """Fetch every chunk of one article (for 'all about Art. X' views)."""
    collection = _get_collection()
    res = collection.get(where={"article_id": article_id})
    return [
        {
            "id": res["ids"][i],
            "text": res["documents"][i],
            "metadata": res["metadatas"][i],
        }
        for i in range(len(res["ids"]))
    ]


def stats():
    try:
        c = _get_collection()
    except Exception as e:
        print(f"❌ No collection. Run `build` first. ({e})")
        return
    print(f"\n📊 Collection: {COLLECTION_NAME}")
    print(f"   Total chunks: {c.count()}")
    sample = c.get(limit=3)
    print(f"   Sample IDs: {sample['ids']}")
    if sample["metadatas"]:
        print(f"   Metadata keys: {list(sample['metadatas'][0].keys())}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m features.ai.rag build")
        print("  python -m features.ai.rag query '<question>'")
        print("  python -m features.ai.rag article <article_id>")
        print("  python -m features.ai.rag stats")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build":
        build()

    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Provide a question.")
            sys.exit(1)
        q = " ".join(sys.argv[2:])
        print(f"\n🔍 Query: {q}")
        print(f"   Detected language: {_detect_lang(q)}\n")
        for i, r in enumerate(query(q, k=6), 1):
            m = r["metadata"]
            print(f"─── Result {i} ───")
            print(f"  {m['article']} — {m['titre_fr']} / {m['titre_ar']}")
            print(f"  law={m['law']}  section={m['section']}  lang={m['lang']}  "
                  f"distance={r['distance']:.4f}")
            print(f"  {r['text'][:260]}…\n")

    elif cmd == "article":
        if len(sys.argv) < 3:
            print("Provide an article_id (e.g. loi77_37_art7).")
            sys.exit(1)
        aid = sys.argv[2]
        chunks = get_article_chunks(aid)
        print(f"\n📖 Article {aid} — {len(chunks)} chunks\n")
        for c in chunks:
            print(f"─── {c['id']}  [{c['metadata']['section']}/{c['metadata']['lang']}] ───")
            print(c["text"])
            print()

    elif cmd == "stats":
        stats()

    else:
        print(f"Unknown command: {cmd}")