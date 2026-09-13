"""
Contract Understanding — Feature 1 (Dalil).

Accepts: PDF, JPG, JPEG, PNG, WEBP, BMP, TIFF — one file or a list (e.g. two images).

Two-step flow
─────────────
STEP 1   extract_and_identify(files)  → VLM extract + LLM structure fields
                                         + RNE / legal completeness check
STEP 2   analyze(contract_data)       → RAG + assessment + explanation + Q&A
         (only after the user has validated the fields)

Q&A      ask_contract(question, ctx)

LANGUAGE POLICY
───────────────
- OCR preserves the source document's language (FR or AR).
- All AI-generated content (analysis, explanations, suggested questions, Q&A)
  is FORCED to FRENCH ONLY. No English, no Arabic in the output.

VLM cascade (fast → slow)
─────────────────────────
1. Groq vision (if USE_GROQ_VISION=1) — off by default
2. Gemini 1.5 Flash                   — fast OCR, ~2–4s
3. Mistral Pixtral-12B                — best on FR/AR legal, ~5–10s
4. Local MinerU (Qwen2-VL 1.2B)       — GPU, private, ~20–40s
5. Tesseract OCR                      — optional

CLI
    python -m features.ai.contract extract <file1> [file2 ...] [--json]
    python -m features.ai.contract analyze <file1> [file2 ...] [--json]
    python -m features.ai.contract ask "<question>" <file1> [file2 ...]
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import requests

# ── Environment shims (must run before transformers/torch) ──
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")

from . import rag  # noqa: E402


# ═══════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

USE_CLOUD_VLM = os.getenv("USE_CLOUD_VLM", "1") == "1"
USE_GROQ_VISION = os.getenv("USE_GROQ_VISION", "0") == "1"
CLOUD_VLM_MAX_DIM = int(os.getenv("CLOUD_VLM_MAX_DIM", "1600"))
CLOUD_VLM_JPEG_Q = int(os.getenv("CLOUD_VLM_JPEG_Q", "88"))

GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "meta-llama/llama-4-scout-17b-16e-instruct",
)
MISTRAL_VISION_MODEL = os.getenv("MISTRAL_VISION_MODEL", "pixtral-12b-2409")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash")

LLM_PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "openai/gpt-oss-20b")
LLM_STRONG_MODEL = os.getenv("LLM_STRONG_MODEL", "openai/gpt-oss-20b")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "ministral-8b-latest")


# ═══════════════════════════════════════════════════════════════════
#  VLM — MinerU (Qwen2-VL based, LOCAL fallback)
# ═══════════════════════════════════════════════════════════════════

VLM_AVAILABLE = False
VLM_IMPORT_ERROR = None
_Qwen2VL = None

try:
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
    from mineru_vl_utils import MinerUClient
    from mineru_vl_utils.post_process import json2md
    VLM_AVAILABLE = True
    _Qwen2VL = Qwen2VLForConditionalGeneration
except ImportError:
    try:
        from transformers import AutoProcessor
        from transformers.models.qwen2_vl import Qwen2VLForConditionalGeneration
        from mineru_vl_utils import MinerUClient
        from mineru_vl_utils.post_process import json2md
        VLM_AVAILABLE = True
        _Qwen2VL = Qwen2VLForConditionalGeneration
    except ImportError:
        try:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
            from mineru_vl_utils import MinerUClient
            from mineru_vl_utils.post_process import json2md
            VLM_AVAILABLE = True
            _Qwen2VL = Qwen2_5_VLForConditionalGeneration
        except ImportError as e3:
            VLM_IMPORT_ERROR = str(e3)

VLM_MODEL_PATH = os.getenv(
    "VLM_MODEL_PATH",
    r"C:\Users\maram\Documents\Orange\Data_Engineering_Pipeline\models\MinerU2.5-Pro-2605-1.2B",
)
VLM_DEVICE = os.getenv("VLM_DEVICE", "auto")
VLM_MAX_PAGES = int(os.getenv("VLM_MAX_PAGES", "8"))
VLM_DPI_SCALE = float(os.getenv("VLM_DPI_SCALE", "2.0"))

PDF_EXTS   = {".pdf"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ALL_EXTS   = PDF_EXTS | IMAGE_EXTS


# ═══════════════════════════════════════════════════════════════════
#  LLM CLIENTS (text)
# ═══════════════════════════════════════════════════════════════════

def _groq_client():
    return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)


def _mistral_client():
    return OpenAI(base_url="https://api.mistral.ai/v1", api_key=MISTRAL_API_KEY)


def _llm(messages, model=None, temperature=0.1, max_tokens=2500) -> str:
    try:
        r = _groq_client().chat.completions.create(
            model=model or LLM_PRIMARY_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        print(f"⚠️  Groq failed: {str(e)[:120]}")
    try:
        r = _mistral_client().chat.completions.create(
            model=LLM_FALLBACK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        print(f"❌ Mistral failed too: {str(e)[:120]}")
        raise


# ═══════════════════════════════════════════════════════════════════
#  CLOUD VLM — Groq + Mistral + Gemini (fast image OCR)
# ═══════════════════════════════════════════════════════════════════

# NOTE: This prompt preserves the SOURCE language of the document on purpose.
# If the contract is Arabic, the OCR returns Arabic; if French, French.
# This is deliberate — we need the raw text to feed the downstream LLM.
# The AI's OUTPUT language is forced to French separately (see prompts below).
_VLM_OCR_PROMPT = (
    "You are an OCR engine for Tunisian commercial-law contracts, which may be "
    "in French, Arabic, or both.\n\n"
    "Extract ALL visible text from this document image exactly as it appears.\n"
    "Rules:\n"
    "- Preserve the reading order and layout: headings, paragraphs, numbered lists, "
    "tables, footers, stamps, and signature blocks.\n"
    "- Keep Arabic text in Arabic; keep French text in French. Do NOT translate.\n"
    "- Preserve accented French characters (é, è, à, ç, ù, ô, î, ï) exactly.\n"
    "- Preserve Arabic diacritics if present.\n"
    "- Preserve numbers, dates, CIN/RC/matricule fiscal digits, and phone numbers "
    "verbatim.\n"
    "- Do NOT add any commentary, summary, translation, or wrapper.\n"
    "- Do NOT invent content. If a region is unreadable, skip it silently.\n"
    "- Output plain markdown."
)


def _encode_image_for_cloud(image_path: str, max_dim: int | None = None) -> tuple[str, str]:
    """Downscale + JPEG-encode an image for cloud VLM upload."""
    from PIL import Image
    import io

    max_dim = max_dim or CLOUD_VLM_MAX_DIM

    with Image.open(image_path) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=CLOUD_VLM_JPEG_Q, optimize=True)
        data = buf.getvalue()

    print(f"   📐 {w}×{h} → {im.size[0]}×{im.size[1]}  ({len(data)/1024:.0f} KB)")
    return base64.b64encode(data).decode("ascii"), "image/jpeg"


def _extract_image_groq(image_path: str) -> str | None:
    """Cloud OCR via Groq vision (only if USE_GROQ_VISION=1)."""
    if not USE_GROQ_VISION:
        return None
    if not GROQ_API_KEY or not USE_CLOUD_VLM:
        return None
    try:
        b64, mime = _encode_image_for_cloud(image_path)
        client = _groq_client()
        r = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _VLM_OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }],
            temperature=0.0,
            max_tokens=4096,
        )
        text = (r.choices[0].message.content or "").strip()
        return text or None
    except Exception as e:
        print(f"   ⚠️  Groq vision failed: {str(e)[:160]}")
        return None


def _extract_image_mistral(image_path: str) -> str | None:
    """Cloud OCR via Mistral Pixtral-12B."""
    if not MISTRAL_API_KEY or not USE_CLOUD_VLM:
        return None
    try:
        b64, mime = _encode_image_for_cloud(image_path)
        client = _mistral_client()
        r = client.chat.completions.create(
            model=MISTRAL_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _VLM_OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }],
            temperature=0.0,
            max_tokens=4096,
        )
        text = (r.choices[0].message.content or "").strip()
        return text or None
    except Exception as e:
        print(f"   ⚠️  Mistral vision failed: {str(e)[:160]}")
        return None


def _extract_image_gemini(image_path: str) -> str | None:
    """Cloud OCR via Google Gemini Flash."""
    if not GEMINI_API_KEY or not USE_CLOUD_VLM:
        return None
    try:
        b64, mime = _encode_image_for_cloud(image_path)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_VISION_MODEL}:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": _VLM_OCR_PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 4096,
            },
        }
        r = requests.post(url, json=payload, timeout=45)
        if r.status_code != 200:
            print(f"   ⚠️  Gemini vision {r.status_code}: {r.text[:120]}")
            return None
        data = r.json()
        cands = data.get("candidates") or []
        if not cands:
            return None
        parts = cands[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception as e:
        print(f"   ⚠️  Gemini vision failed: {str(e)[:160]}")
        return None


def _extract_image_cloud(image_path: str) -> tuple[str | None, str | None]:
    """Try cloud VLMs in order: Groq (if on) → Gemini → Mistral."""
    if USE_GROQ_VISION:
        t0 = time.time()
        text = _extract_image_groq(image_path)
        if text and len(text) >= 60:
            print(f"   ✅ groq ({len(text)} chars, {time.time()-t0:.1f}s)")
            return text, "groq"

    t2 = time.time()
    text = _extract_image_gemini(image_path)
    if text and len(text) >= 60:
        print(f"   ✅ gemini ({len(text)} chars, {time.time()-t2:.1f}s)")
        return text, "gemini"

    t1 = time.time()
    text = _extract_image_mistral(image_path)
    if text and len(text) >= 60:
        print(f"   ✅ mistral ({len(text)} chars, {time.time()-t1:.1f}s)")
        return text, "mistral"

    return None, None


# ═══════════════════════════════════════════════════════════════════
#  LOCAL VLM — MinerU (Qwen2-VL 1.2B)
# ═══════════════════════════════════════════════════════════════════

class _MinerUExtractor:
    """Singleton local VLM (Qwen2-VL 1.2B via MinerU)."""

    _instance = None

    def __init__(self):
        self.client = None
        self.loaded = False
        self.error = None
        self.device_used = None
        self.dtype_used = None
        if VLM_AVAILABLE:
            self._load()

    @classmethod
    def get(cls) -> "_MinerUExtractor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self):
        try:
            import torch

            if not os.path.exists(VLM_MODEL_PATH):
                raise FileNotFoundError(f"VLM model not found: {VLM_MODEL_PATH}")

            print(f"🤖 Loading MinerU VLM from: {VLM_MODEL_PATH}")

            if VLM_DEVICE == "auto":
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
            else:
                device = VLM_DEVICE

            dtype = torch.float16 if str(device).startswith("cuda") else torch.float32

            print(f"   📦 device = {device} | dtype = {dtype}")
            if str(device).startswith("cuda") and torch.cuda.is_available():
                print(f"   🎮 GPU: {torch.cuda.get_device_name(0)}")
                print(f"   💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

            model = _Qwen2VL.from_pretrained(
                VLM_MODEL_PATH,
                torch_dtype=dtype,
                device_map=device if str(device).startswith("cuda") else None,
                low_cpu_mem_usage=True,
                local_files_only=True,
            )
            if not str(device).startswith("cuda"):
                model = model.to(device)

            processor = AutoProcessor.from_pretrained(
                VLM_MODEL_PATH, use_fast=True, local_files_only=True
            )

            self.client = MinerUClient(
                backend="transformers",
                model=model,
                processor=processor,
                image_analysis=False,
            )
            self.loaded = True
            self.device_used = device
            self.dtype_used = str(dtype)
            print("✅ MinerU VLM loaded")

        except Exception as e:
            self.error = str(e)[:300]
            print(f"⚠️  VLM load failed: {self.error}")

    def extract_image_local(self, image_path: str) -> str:
        if not self.loaded or not self.client:
            raise RuntimeError(
                f"MinerU VLM not available. {self.error or VLM_IMPORT_ERROR or 'unknown'}"
            )
        from PIL import Image

        with Image.open(image_path) as im:
            im = im.convert("RGB")
            content_list = self.client.two_step_extract(im)
            return json2md(content_list)

    def extract_pil_local(self, img) -> str:
        if not self.loaded or not self.client:
            raise RuntimeError("MinerU VLM not available")
        content_list = self.client.two_step_extract(img)
        return json2md(content_list)


# ═══════════════════════════════════════════════════════════════════
#  INPUT HELPERS
# ═══════════════════════════════════════════════════════════════════

def _normalize_inputs(files: str | list[str]) -> list[str]:
    if isinstance(files, (str, Path)):
        files = [files]
    out = []
    for f in files:
        p = str(f)
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        ext = os.path.splitext(p)[1].lower()
        if ext not in ALL_EXTS:
            raise ValueError(
                f"Unsupported file type: {ext}  (supported: {sorted(ALL_EXTS)})"
            )
        out.append(p)
    return out


def _tesseract_ocr(pil_image) -> str:
    try:
        import pytesseract
        cmd = os.getenv("TESSERACT_CMD")
        if cmd and os.path.exists(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
        return pytesseract.image_to_string(pil_image, lang="fra+ara").strip()
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC — extract from mixed files (PDF + images)
# ═══════════════════════════════════════════════════════════════════

def extract_document(files: str | list[str]) -> dict:
    t_all = time.time()
    paths = _normalize_inputs(files)
    extractor = _MinerUExtractor.get()

    print(f"⏱️  Extraction started — {len(paths)} file(s)")
    print(f"   Cloud VLM: {'ON' if USE_CLOUD_VLM else 'OFF'}"
          f"  | Groq vision: {'on' if USE_GROQ_VISION else 'off'}"
          f"  | Mistral: {'yes' if MISTRAL_API_KEY else 'no'}"
          f"  | Gemini: {'yes' if GEMINI_API_KEY else 'no'}"
          f"  | MinerU: {'ready' if extractor.loaded else 'no'}")

    all_md: list[str] = []
    sources: list[dict] = []
    total_units = 0

    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)

        if ext in PDF_EXTS:
            print(f"📄 Extracting PDF: {name}")
            pages_md, engines = _extract_pdf_smart(path, extractor)
            all_md.extend(pages_md)
            total_units += len(pages_md)
            sources.append({
                "path": path, "kind": "pdf",
                "pages": len(pages_md), "engines": engines,
            })

        elif ext in IMAGE_EXTS:
            print(f"🖼️  Extracting image: {name}")
            md, engine = _extract_single_image(path, extractor)
            all_md.append(md)
            total_units += 1
            sources.append({
                "path": path, "kind": "image",
                "pages": 1, "engines": [engine],
            })

    print(f"⏱️  Extraction finished in {time.time()-t_all:.1f}s")

    return {
        "markdown": "\n\n---\n\n".join(all_md),
        "pages": total_units,
        "sources": sources,
    }


def _extract_single_image(image_path: str, extractor: "_MinerUExtractor") -> tuple[str, str]:
    t0 = time.time()

    text, engine = _extract_image_cloud(image_path)
    if text:
        return text, engine

    if extractor.loaded:
        try:
            t1 = time.time()
            text = extractor.extract_image_local(image_path)
            print(f"   🧠 mineru ({len(text)} chars, {time.time()-t1:.1f}s)")
            if text.strip():
                return text.strip(), "mineru"
        except Exception as e:
            print(f"   ⚠️  MinerU failed: {str(e)[:100]}")

    try:
        from PIL import Image
        t1 = time.time()
        with Image.open(image_path) as im:
            text = _tesseract_ocr(im.convert("RGB"))
        if text:
            print(f"   🔤 tesseract ({len(text)} chars, {time.time()-t1:.1f}s)")
            return text, "tesseract"
    except Exception:
        pass

    raise RuntimeError(f"All extraction methods failed for {image_path}")


def _extract_pdf_smart(pdf_path: str, extractor: "_MinerUExtractor") -> tuple[list[str], list[str]]:
    import fitz
    from PIL import Image

    t0 = time.time()
    pages_md: list[str] = []
    engines: list[str] = []

    doc = fitz.open(pdf_path)
    try:
        n = min(doc.page_count, VLM_MAX_PAGES)
        print(f"   📖 PDF has {doc.page_count} pages (processing {n})")

        for i in range(n):
            tp = time.time()
            page = doc[i]
            embedded = (page.get_text() or "").strip()

            if len(embedded) >= 80:
                pages_md.append(embedded)
                engines.append("pymupdf")
                print(f"   ⚡ Page {i+1}: pymupdf ({len(embedded)} chars, "
                      f"{(time.time()-tp)*1000:.0f}ms)")
                continue

            pix = page.get_pixmap(matrix=fitz.Matrix(VLM_DPI_SCALE, VLM_DPI_SCALE))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    img.save(tmp.name, "JPEG", quality=CLOUD_VLM_JPEG_Q, optimize=True)
                    tmp_path = tmp.name

                text, engine = _extract_image_cloud(tmp_path)
                if text:
                    pages_md.append(text)
                    engines.append(engine)
                    print(f"   🧠 Page {i+1}: {engine} ({len(text)} chars, "
                          f"{time.time()-tp:.1f}s)")
                    continue

                if extractor.loaded:
                    try:
                        t1 = time.time()
                        text = extractor.extract_pil_local(img)
                        if text.strip():
                            pages_md.append(text.strip())
                            engines.append("mineru")
                            print(f"   🧠 Page {i+1}: mineru ({len(text)} chars, "
                                  f"{time.time()-t1:.1f}s)")
                            continue
                    except Exception as e:
                        print(f"   ⚠️  MinerU failed on page {i+1}: {str(e)[:80]}")

                text = _tesseract_ocr(img)
                if text:
                    pages_md.append(text)
                    engines.append("tesseract")
                    print(f"   🔤 Page {i+1}: tesseract ({len(text)} chars, "
                          f"{time.time()-tp:.1f}s)")
                    continue

                pages_md.append(embedded)
                engines.append("raw")
                print(f"   ⚠️  Page {i+1}: no extractor succeeded")

            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

    finally:
        doc.close()

    print(f"   ✅ PDF done in {time.time()-t0:.1f}s  "
          f"(engines: {', '.join(engines)})")
    return pages_md, engines


def extract_pdf_text(pdf_path: str) -> dict:
    return extract_document(pdf_path)


# ═══════════════════════════════════════════════════════════════════
#  TEXT LLM HELPERS
# ═══════════════════════════════════════════════════════════════════

def _extract_json(text: str) -> dict:
    if not text:
        return {}
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        text = m.group(1)
    else:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            text = text[s : e + 1]
    try:
        return json.loads(text)
    except Exception:
        return {}


def _clean(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate(text: str, max_chars: int = 20000) -> str:
    return text if len(text) <= max_chars else text[:max_chars] + "\n\n[... truncated ...]"


def _force_french(text: str) -> str:
    """Strip any obvious English artifacts from the LLM output."""
    if not text:
        return text
    # Replace common English transition words that leak when the LLM drifts
    replacements = {
        r"\bThe contract\b": "Le contrat",
        r"\bThe law\b": "La loi",
        r"\bHowever\b": "Toutefois",
        r"\bTherefore\b": "Par conséquent",
        r"\bSummary\b": "Résumé",
        r"\bOverview\b": "Aperçu",
        r"\bRisk level\b": "Niveau de risque",
        r"\bCompliant\b": "Conforme",
    }
    for pat, repl in replacements.items():
        text = re.sub(pat, repl, text)
    return text


# ═══════════════════════════════════════════════════════════════════
#  FRENCHISM SCRUBBER
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


def _scrub_deep(obj):
    if isinstance(obj, str):
        return _force_french(_scrub_frenchism(obj))
    if isinstance(obj, dict):
        return {k: _scrub_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_deep(x) for x in obj]
    return obj


# ═══════════════════════════════════════════════════════════════════
#  ARTICLE VERIFICATION (against RAG chunks)
# ═══════════════════════════════════════════════════════════════════

def _collect_valid_article_numbers(chunks: list[dict]) -> set[str]:
    nums: set[str] = set()
    for r in chunks:
        meta = r.get("metadata", {})
        art = str(meta.get("article", ""))
        for n in re.findall(r"\d+", art):
            nums.add(n)
        text = r.get("text", "")
        for m in re.finditer(r"(?:Article|الفصل)\s*(\d+)", text, re.IGNORECASE):
            nums.add(m.group(1))
    return nums


def _article_is_verified(article_str: str, valid_nums: set[str]) -> bool:
    if not article_str:
        return False
    nums = re.findall(r"\d+", article_str)
    return any(n in valid_nums for n in nums)


def _verify_analysis_articles(analysis: dict, chunks: list[dict]) -> dict:
    valid = _collect_valid_article_numbers(chunks)
    risks = (analysis.get("assessment") or {}).get("risks") or []
    for r in risks:
        art = r.get("article", "")
        if art and not _article_is_verified(art, valid):
            r["article"] = ""
    return analysis


# ═══════════════════════════════════════════════════════════════════
#  DETERMINISTIC SUGGESTED QUESTIONS — FRENCH ONLY
# ═══════════════════════════════════════════════════════════════════

def _build_suggested_questions(
    missing_blocking: list[str],
    missing_warning: list[str],
    risks: list[dict],
    lang: str = "fr",          # kept for API compat; ignored — always FR
) -> list[str]:
    """Suggested questions are ALWAYS generated in French."""
    qs: list[str] = []

    for lbl in missing_blocking[:3]:
        qs.append(f"Le contrat contient-il bien « {lbl} » ? Comment le compléter ?")

    for r in risks[:2]:
        issue = (r.get("issue") or "").strip()
        if issue:
            qs.append(f"Que faire face à : {issue} ?")

    if len(qs) < 4:
        qs.extend([
            "Quelles sont les formalités obligatoires après signature ?",
            "Quels sont mes droits et mes obligations principaux ?",
            "Le contrat est-il conforme au Code de Commerce tunisien ?",
            "Quels sont les délais à respecter ?",
        ])

    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:6]


# ═══════════════════════════════════════════════════════════════════
#  REQUIREMENTS — loaded from JSON
# ═══════════════════════════════════════════════════════════════════

AI_DIR = Path(__file__).resolve().parent
REQUIREMENTS_PATH = AI_DIR / "data" / "contract_requirements.json"


def _load_requirements() -> dict:
    if not REQUIREMENTS_PATH.exists():
        print(f"⚠️  Missing requirements file: {REQUIREMENTS_PATH}")
        return {}
    with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_REQUIREMENTS = _load_requirements()


def _find_contract_type(contract_type: str) -> tuple[str | None, dict | None]:
    ctypes = _REQUIREMENTS.get("contract_types", {})
    if not ctypes:
        return None, None

    ct = (contract_type or "").strip().lower()
    if not ct:
        return None, None

    for tid, tdata in ctypes.items():
        if tid == ct:
            return tid, tdata

    for tid, tdata in ctypes.items():
        aliases = [a.lower() for a in tdata.get("aliases_fr", [])] \
                + [a.lower() for a in tdata.get("aliases_ar", [])]
        if tid in ct or ct in tid:
            return tid, tdata
        for a in aliases:
            if a and (a in ct or ct in a):
                return tid, tdata

    return None, None


def _check_contract_completeness(contract_type: str, fields: dict) -> dict:
    tid, req = _find_contract_type(contract_type)
    if not req:
        return {
            "matched_type": None,
            "present": [], "empty": [],
            "present_count": 0, "empty_count": 0, "total": 0,
            "blocking_missing": [], "warning_missing": [],
            "note": f"No checklist found for contract type: {contract_type!r}",
        }

    present, empty = [], []
    for item in req.get("mandatory_items", []):
        field = item.get("extraction_field", "")
        val = (fields.get(field) or "").strip() if field else ""
        entry = {
            "id": item.get("id", ""),
            "group": item.get("group", ""),
            "label_fr": item.get("label_fr", ""),
            "label_ar": item.get("label_ar", ""),
            "legal_basis": item.get("legal_basis", ""),
            "severity": item.get("severity", "info"),
            "why": item.get("why", ""),
        }
        if val:
            entry["value"] = val
            present.append(entry)
        else:
            empty.append(entry)

    blocking_missing = [e["label_fr"] for e in empty if e["severity"] == "blocking"]
    warning_missing  = [e["label_fr"] for e in empty if e["severity"] == "warning"]

    return {
        "matched_type": tid,
        "label_fr": req.get("label_fr", ""),
        "label_ar": req.get("label_ar", ""),
        "legal_governance": req.get("legal_governance", []),
        "present": present,
        "empty": empty,
        "present_count": len(present),
        "empty_count": len(empty),
        "total": len(present) + len(empty),
        "blocking_missing": blocking_missing,
        "warning_missing": warning_missing,
    }


def get_post_signature_formalities(contract_type: str) -> list[dict]:
    tid, _ = _find_contract_type(contract_type)
    if not tid:
        return []
    return _REQUIREMENTS.get("post_signature_formalities", {}).get(tid, [])


# ═══════════════════════════════════════════════════════════════════
#  STEP 1 — Extraction + Identification + Completeness
# ═══════════════════════════════════════════════════════════════════

_IDENTIFY_PROMPT = """You analyze a Tunisian commercial-law contract extracted from a file (PDF pages or images) by OCR.

The contract may be in French or Arabic. It may be of any type (bail commercial,
location-gérance / gérance libre, cession de fonds de commerce, autre).

═══════════════════════════════════════════════════════════
LANGUAGE RULES — STRICT
═══════════════════════════════════════════════════════════
- The extracted FIELD VALUES (names, dates, addresses, amounts, clause text…)
  must stay in the ORIGINAL language of the contract.
- BUT the following AI-generated fields MUST be written in FRENCH ONLY:
  * "summary_short"
  * every string in "notes"
  * every string in "key_terms"
- NEVER write English anywhere. If you are about to write an English word,
  use the French equivalent instead.

═══════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════
Return ONLY a JSON object with these keys:

{
  "language": "fr" | "ar",
  "contract_type": "bail commercial | location-gerance | cession-fonds-commerce | autre",
  "parties": {
    "bailleur": "owner / propriétaire du fonds / bailleur (if applicable)",
    "preneur": "gérant libre / locataire / preneur / acquéreur (if applicable)",
    "other": "any other party (avocat, témoins)"
  },
  "fields": {
    "date_signature": "",
    "date_effet": "",
    "duree": "",
    "bailleur_nom_complet": "",
    "bailleur_cin": "",
    "bailleur_adresse": "",
    "bailleur_matricule": "",
    "preneur_nom_complet": "",
    "preneur_cin": "",
    "preneur_adresse": "",
    "preneur_matricule": "",
    "fonds_description": "",
    "fonds_adresse": "",
    "fonds_activite": "",
    "fonds_ancien_rc": "",
    "fonds_nouveau_rc": "",
    "redevance_montant": "",
    "redevance_periodicite": "",
    "depot_garantie": "",
    "loyer_montant": "",
    "adresse_bien": "",
    "activite_autorisee": "",
    "chiffre_affaires": "",
    "benefices": "",
    "bail_details": "",
    "clause_nantissements": "",
    "clause_renouvellement": "",
    "clause_resiliation": "",
    "clause_sous_location": "",
    "clause_ameliorations": "",
    "clause_duree_interdiction": "",
    "clause_dissipation": "",
    "clause_publication": "",
    "avocat_redacteur": "",
    "avocat_consultation_rc": "",
    "avocat_information_parties": "",
    "avocat_formalites": "",
    "mention_gérant_libre": "",
    "signatures": ""
  },
  "summary_short": "Résumé de 2 à 3 phrases EN FRANÇAIS sur ce contrat",
  "key_terms": ["3 à 6 termes clés EN FRANÇAIS"],
  "notes": ["observations EN FRANÇAIS sur l'ambiguïté, l'illisibilité ou un contenu inhabituel"]
}

Rules:
- Empty string "" when the value is NOT in the text — NEVER guess.
- For clause_* fields: put a short phrase from the text if present, or "" if absent.
- avocat_redacteur: put the avocat's name if the text says who drafted it, else "".
- avocat_consultation_rc: "oui" if the text says the avocat consulted the RC/nantissements, else "".
- avocat_information_parties: "oui" if the text says the avocat informed the parties, else "".
- mention_gérant_libre: "oui" if the text mentions "gérant libre" / "مستغل حر", else "".
- signatures: "oui" if signatures are visible, else "".
- summary_short, key_terms and notes: FRENCH ONLY.

Contract text:
\"\"\"
__CONTRACT_TEXT__
\"\"\"
"""


def extract_and_identify(files: str | list[str]) -> dict:
    print("🔍 Extracting content via VLM…")
    extracted = extract_document(files)
    md = extracted["markdown"]
    if not md.strip():
        raise RuntimeError("All VLM/OCR engines returned empty text.")

    print("🧠 Structuring fields…")
    prompt = _IDENTIFY_PROMPT.replace("__CONTRACT_TEXT__", _truncate(md))
    id_raw = _llm(
        [
            {"role": "system", "content": "You output only valid JSON. You write summary_short, key_terms and notes in FRENCH. No prose."},
            {"role": "user", "content": prompt},
        ],
        model=LLM_STRONG_MODEL,
        temperature=0.0,
        max_tokens=2000,
    )
    ident = _extract_json(id_raw)
    ident = _scrub_deep(ident)

    fields = ident.get("fields", {})

    completeness = _check_contract_completeness(
        ident.get("contract_type", ""),
        fields,
    )
    formalities = get_post_signature_formalities(ident.get("contract_type", ""))

    return {
        "extraction": {
            "pages": extracted["pages"],
            "markdown": md,
            "sources": extracted["sources"],
        },
        "identification": ident,
        "completeness": completeness,
        "post_signature_formalities": formalities,
        "status": "awaiting_validation",
    }


# ═══════════════════════════════════════════════════════════════════
#  STEP 2 — Analysis + Explanation + Questions
# ═══════════════════════════════════════════════════════════════════

_ANALYZE_PROMPT = """Tu es Dalil (دليل), un assistant juridique tunisien spécialisé dans les fonds de commerce (Loi 77-37 + Code de Commerce).

On te fournit :
1. Les données du contrat validées par l'utilisateur (JSON).
2. La liste des éléments légaux obligatoires MANQUANTS dans le contrat.
3. Les articles de loi tunisiens pertinents récupérés depuis une base vectorielle.

═══════════════════════════════════════════════════════════
RÈGLE DE LANGUE ABSOLUE
═══════════════════════════════════════════════════════════
Tu produis TOUT EN FRANÇAIS. AUCUN mot anglais. AUCUN mot arabe.
Même si le contrat est en arabe, ta réponse est 100% en français.

Si tu es tenté d'écrire un mot anglais, utilise son équivalent français.
Exemples :
- "summary" → "résumé"
- "risk" → "risque"
- "contract" → "contrat"
- "compliant" → "conforme"
- "issue" → "problème"
- "detail" → "détail"
- "note" → "remarque"
- "however" → "toutefois"
- "therefore" → "par conséquent"

═══════════════════════════════════════════════════════════
FORMAT DE SORTIE
═══════════════════════════════════════════════════════════
Retourne UNIQUEMENT un objet JSON avec cette structure exacte.
Pas de markdown, pas de gras (**), pas de titres (#), pas de prose hors JSON.

{
  "validation": {
    "present": [ "libellés courts en FRANÇAIS des éléments trouvés dans le contrat" ],
    "missing_legal": [ "libellés courts en FRANÇAIS des éléments obligatoires absents" ],
    "warnings": [ "problèmes potentiels ou clauses ambiguës, en FRANÇAIS, une phrase courte chacun" ]
  },
  "assessment": {
    "compliant": true | false,
    "risk_level": "low" | "medium" | "high",
    "risks": [
      { "issue": "titre court EN FRANÇAIS", "detail": "1 à 2 phrases EN FRANÇAIS", "article": "Article X de la loi 77-37 ou du Code de Commerce" }
    ],
    "notes": [ "1 à 3 remarques juridiques courtes EN FRANÇAIS" ]
  },
  "explanation": {
    "for_bailleur": {
      "what_it_means": "2 à 3 phrases EN FRANÇAIS",
      "your_rights": ["3 à 5 puces EN FRANÇAIS"],
      "to_avoid": ["3 à 5 puces EN FRANÇAIS"]
    },
    "for_commercant": {
      "what_it_means": "2 à 3 phrases EN FRANÇAIS",
      "your_rights": ["3 à 5 puces EN FRANÇAIS"],
      "to_avoid": ["3 à 5 puces EN FRANÇAIS"]
    }
  }
}

═══════════════════════════════════════════════════════════
TERMINOLOGIE TUNISIENNE — OBLIGATOIRE
═══════════════════════════════════════════════════════════
❌ INTERDIT : BODACC, INPI, Kbis, RCS, "registre du commerce" (dire RNE),
              "tribunal de commerce" (dire Tribunal de Première Instance).
✅ CORRECT : RNE, JORT, Greffe du Tribunal de Première Instance,
             Huissier de justice, Recette des Finances, Municipalité, APC.

═══════════════════════════════════════════════════════════
DONNÉES DU CONTRAT
═══════════════════════════════════════════════════════════
__CONTRACT_DATA__

═══════════════════════════════════════════════════════════
ÉLÉMENTS OBLIGATOIRES MANQUANTS
═══════════════════════════════════════════════════════════
__MISSING_LEGAL__

═══════════════════════════════════════════════════════════
CONTEXTE JURIDIQUE RÉCUPÉRÉ
═══════════════════════════════════════════════════════════
__LEGAL_CONTEXT__

═══════════════════════════════════════════════════════════
RÈGLES FINALES
═══════════════════════════════════════════════════════════
- Base-toi UNIQUEMENT sur le contexte récupéré pour citer des articles.
- N'invente JAMAIS un numéro d'article. En cas de doute, laisse "article" vide.
- Réponse 100% en français. Jamais d'anglais, jamais d'arabe.
- Si le contrat est une "location-gérance" / "gérance libre" :
  traite "bailleur" comme "propriétaire du fonds" et "preneur" comme "gérant libre".
- Renvoie UNIQUEMENT le JSON, sans texte avant ni après.
"""


def _rag_chunks_for_contract(contract_type: str, fields: dict, k: int = 12) -> list[dict]:
    keywords = [contract_type or "bail commercial"]
    for key in (
        "clause_resiliation", "clause_renouvellement",
        "clause_sous_location", "clause_ameliorations",
        "clause_dissipation", "clause_publication",
    ):
        if fields.get(key):
            keywords.append(key.replace("clause_", "").replace("_", " "))

    if fields.get("redevance_montant"):
        keywords.append("redevance loyer")
    if fields.get("fonds_description"):
        keywords.append("fonds de commerce")
    if fields.get("avocat_redacteur"):
        keywords.append("avocat rédaction acte")

    query = " ".join(keywords)
    lang = rag._detect_lang(query)
    return rag.query(query, k=k, lang=lang)


def _format_rag_context(chunks: list[dict]) -> str:
    parts = []
    for i, r in enumerate(chunks, 1):
        m = r["metadata"]
        parts.append(
            f"--- Source {i} ---\n"
            f"{m['article']} ({m['titre_fr']} / {m['titre_ar']})\n"
            f"{r['text']}\n"
        )
    return "\n".join(parts) if parts else "(no relevant articles)"


def analyze(contract_data: dict, completeness: dict | None = None) -> dict:
    ctype = contract_data.get("contract_type", "")
    fields = contract_data.get("fields", {})

    missing_blocking = (completeness or {}).get("blocking_missing", [])
    missing_warning = (completeness or {}).get("warning_missing", [])
    missing_labels = missing_blocking + missing_warning

    print("📚 Retrieving relevant law…")
    chunks = _rag_chunks_for_contract(ctype, fields, k=12)
    legal_context = _format_rag_context(chunks)

    print("⚖️  Analyzing contract…")
    prompt = (
        _ANALYZE_PROMPT
        .replace("__CONTRACT_DATA__", json.dumps(contract_data, ensure_ascii=False, indent=2))
        .replace("__MISSING_LEGAL__", json.dumps(missing_labels, ensure_ascii=False, indent=2))
        .replace("__LEGAL_CONTEXT__", legal_context)
    )
    raw = _llm(
        [
            {"role": "system", "content": "Tu réponds UNIQUEMENT en français, et tu produis UNIQUEMENT du JSON valide. Aucune prose."},
            {"role": "user", "content": prompt},
        ],
        model=LLM_STRONG_MODEL,
        temperature=0.2,
        max_tokens=3500,
    )
    analysis = _extract_json(raw)

    analysis = _scrub_deep(analysis)
    analysis = _verify_analysis_articles(analysis, chunks)

    risks = (analysis.get("assessment") or {}).get("risks") or []
    suggested = _build_suggested_questions(
        missing_blocking, missing_warning, risks, lang="fr"
    )

    return {
        "validation": analysis.get(
            "validation", {"present": [], "missing_legal": [], "warnings": []}
        ),
        "assessment": analysis.get(
            "assessment",
            {"compliant": None, "risk_level": "unknown", "risks": [], "notes": []},
        ),
        "explanation": analysis.get(
            "explanation", {"for_bailleur": {}, "for_commercant": {}}
        ),
        "suggested_questions": suggested,
        "status": "analyzed",
    }


# ═══════════════════════════════════════════════════════════════════
#  Q&A — FRENCH ONLY
# ═══════════════════════════════════════════════════════════════════

_QA_SYSTEM_PROMPT = """Tu es Dalil (دليل), l'assistant juridique intégré au service Compréhension du contrat de la plateforme Dalil.

═══════════════════════════════════════════════════════════
RÈGLE DE LANGUE ABSOLUE — LA PLUS IMPORTANTE
═══════════════════════════════════════════════════════════
Tu réponds TOUJOURS EN FRANÇAIS, quelle que soit la langue de la question de l'utilisateur.
- Si l'utilisateur écrit en anglais → tu réponds en français.
- Si l'utilisateur écrit en arabe → tu réponds en français.
- Si l'utilisateur écrit en français → tu réponds en français.
AUCUN mot anglais. AUCUN mot arabe. 100% FRANÇAIS.

Si tu es tenté d'écrire un mot anglais, utilise son équivalent français :
- "summary" → "résumé"
- "contract" → "contrat"
- "clause" → "clause" (identique)
- "risk" → "risque"
- "next step" → "prochaine étape"
- "however" → "toutefois"
- "therefore" → "par conséquent"
- "here is" → "voici"

═══════════════════════════════════════════════════════════
TA PERSONNALITÉ
═══════════════════════════════════════════════════════════
Tu es un guide juridique chaleureux et patient — pas un moteur de recherche.
L'utilisateur vient de téléverser un contrat et te pose une question à son sujet.
Tu prends le temps de relier ce que DIT le contrat à ce que DIT la loi, dans sa situation précise.
Tu ne listes jamais des faits sans contexte. Tu relies toujours les faits à leur document et à leur prochaine étape.

═══════════════════════════════════════════════════════════
PÉRIMÈTRE
═══════════════════════════════════════════════════════════
Tu réponds aux questions sur les contrats commerciaux tunisiens :
- Bail commercial (Loi 77-37)
- Location-gérance / gérance libre (Code de Commerce, art. 229–234, 467)
- Cession de fonds de commerce (Code de Commerce, art. 189–228)

═══════════════════════════════════════════════════════════
LES TROIS MOUVEMENTS DE CHAQUE RÉPONSE
═══════════════════════════════════════════════════════════

**Mouvement 1 — Accusé de réception (1 phrase)**
Reformule la question de l'utilisateur, dans le contexte de SON contrat.

**Mouvement 2 — Le cœur de la réponse (ancré dans le contrat)**

Ce que dit votre contrat
- <fait réellement présent dans le JSON du contrat>
- <fait 2>

Ce que dit la loi
- <point juridique, avec article>
- <point juridique 2, avec article>

Points d'attention
- <écart, risque ou ambiguïté dans le contrat>

**Mouvement 3 — Invitation à continuer (1-2 phrases)**
Termine par une action concrète (« Prochaine étape »)
ou une question de suivi si la réponse dépend d'une information que tu n'as pas.
Ne termine jamais à plat.

═══════════════════════════════════════════════════════════
LONGUEUR DE LA RÉPONSE — ADAPTE-TOI À LA QUESTION
═══════════════════════════════════════════════════════════
- Question factuelle simple → 2 à 3 phrases courtes. Pas de titres.
- Vraie question juridique → utilise la structure en 3 sections ci-dessus.
- Demande explicite de détail (« explique en détail ») → jusqu'à 8 puces.

═══════════════════════════════════════════════════════════
RÈGLES DE FORMATAGE — STRICT
═══════════════════════════════════════════════════════════
- PAS de gras markdown (**), pas d'italique (*), pas de titres (#).
- Texte brut. Puces : « - » en début de ligne.
- Ligne vide entre les sections.

═══════════════════════════════════════════════════════════
TERMINOLOGIE TUNISIENNE — STRICT
═══════════════════════════════════════════════════════════
- N'utilise JAMAIS de termes français de France :
  ❌ BODACC, INPI, Kbis, RCS, « registre du commerce » (dire RNE),
    « tribunal de commerce » (dire Tribunal de Première Instance).
- ✅ RNE, JORT, Greffe du Tribunal de Première Instance,
     Huissier de justice, Recette des Finances, Municipalité, APC.

═══════════════════════════════════════════════════════════
RÈGLES ABSOLUES
═══════════════════════════════════════════════════════════
- Réponds UNIQUEMENT en français. Jamais d'anglais, jamais d'arabe.
- Base-toi UNIQUEMENT sur le contexte juridique récupéré et les données du contrat fournies.
- Si le contrat ne contient pas la réponse, dis-le explicitement.
- Cite toujours le(s) article(s) utilisé(s) quand tu fais une affirmation juridique.
- N'invente jamais de numéro d'article, de délai ou de montant.
- Si le contrat est une location-gérance, traite « bailleur » comme « propriétaire du fonds » et « preneur » comme « gérant libre ».
- Termine toujours par la ligne « prochaine étape » ou « question de suivi ».
- Parle comme un conseiller de confiance qui connaît la loi et se soucie du document de l'utilisateur.
"""


def ask_contract(
    question: str,
    contract_context: dict,
    history: list | None = None,
    k: int = 6,
) -> dict:
    history = history or []
    q = (question or "").strip()
    if not q:
        raise ValueError("Empty question")

    # Force lang = "fr" everywhere for the answer, regardless of question language
    lang = "fr"

    ident = contract_context.get("identification", contract_context)
    fields = ident.get("fields", {})
    ctype = ident.get("contract_type", "")

    # RAG query — mix question + contract type + field values.
    # Fall back to French RAG retrieval since the answer will be French.
    rag_query = f"{q} {ctype} {' '.join(str(v) for v in fields.values() if v)[:300]}"
    chunks = rag.query(rag_query, k=k, lang="fr")
    legal_context = _format_rag_context(chunks)

    contract_summary = json.dumps(
        {
            "type": ctype,
            "parties": ident.get("parties", {}),
            "fields": fields,
            "summary": ident.get("summary_short", ""),
        },
        ensure_ascii=False,
        indent=2,
    )

    user_msg = (
        f"## Données du contrat\n{contract_summary}\n\n"
        f"## Contexte juridique récupéré\n{legal_context}\n\n"
        f"## Question de l'utilisateur\n{q}\n\n"
        f"RAPPEL : ta réponse est 100% EN FRANÇAIS, jamais en anglais, jamais en arabe."
    )

    messages = [
        {"role": "system", "content": _QA_SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_msg},
    ]
    answer = _clean(_llm(messages, temperature=0.2, max_tokens=1500))
    answer = _force_french(_scrub_frenchism(answer))

    valid = _collect_valid_article_numbers(chunks)
    def _fix_article(match):
        num = match.group(1)
        return match.group(0) if num in valid else ""
    answer = re.sub(
        r"(?:Article|الفصل)\s*(\d+)(?:\s+(?:de la loi|du Code|من القانون|من المجلة)[^.,\n]*)",
        _fix_article,
        answer,
    )

    return {
        "answer": answer,
        "lang": "fr",   # always French
        "sources": [
            {
                "id": r["id"],
                "article": r["metadata"]["article"],
                "title_fr": r["metadata"]["titre_fr"],
                "title_ar": r["metadata"]["titre_ar"],
                "law": r["metadata"]["law"],
            }
            for r in chunks
        ],
    }


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def _cli():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m features.ai.contract extract <file1> [file2 ...] [--json]")
        print("  python -m features.ai.contract analyze <file1> [file2 ...] [--json]")
        print("  python -m features.ai.contract ask '<question>' <file1> [file2 ...]")
        print()
        print("Supported: PDF, JPG, PNG, WEBP, BMP, TIFF — one or multiple files.")
        sys.exit(1)

    cmd = sys.argv[1]

    raw_args = sys.argv[2:]
    files = [a for a in raw_args if a and not a.startswith("--")]

    if cmd == "extract":
        if not files:
            print("Provide at least one file (PDF or image)."); sys.exit(1)
        r = extract_and_identify(files)
        if "--json" in raw_args:
            print(json.dumps(r, ensure_ascii=False, indent=2))
            return
        ident = r["identification"]
        comp = r["completeness"]
        print(f"\n✅ Extracted {r['extraction']['pages']} unit(s) from {len(r['extraction']['sources'])} file(s)")
        for s in r["extraction"]["sources"]:
            print(f"   {os.path.basename(s['path'])}: engines={s.get('engines', [])}")
        print(f"📄 Type: {ident.get('contract_type')}   🌍 lang: {ident.get('language')}")
        print(f"🔎 Matched checklist: {comp.get('matched_type')} — {comp.get('label_fr')}")
        print(f"\n🎯 Completeness: {comp['present_count']}/{comp['total']} present")
        print(f"   ❌ Blocking missing: {len(comp['blocking_missing'])}")
        print(f"   ⚠️  Warning missing:  {len(comp['warning_missing'])}")
        if comp["blocking_missing"]:
            print("\n🚨 BLOCKING MISSING:")
            for lbl in comp["blocking_missing"]:
                print(f"   ✘ {lbl}")
        if comp["warning_missing"]:
            print("\n⚠️  WARNINGS:")
            for lbl in comp["warning_missing"]:
                print(f"   ⚠ {lbl}")
        if r["post_signature_formalities"]:
            print("\n📅 POST-SIGNATURE FORMALITIES:")
            for f in r["post_signature_formalities"]:
                print(f"   • {f.get('label_fr')}  ({f.get('legal_basis')})")

    elif cmd == "analyze":
        if not files:
            print("Provide at least one file (PDF or image)."); sys.exit(1)
        step1 = extract_and_identify(files)
        step2 = analyze(step1["identification"], completeness=step1["completeness"])
        result = {**step1, **step2}
        if "--json" in raw_args:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        v = step2["validation"]; a = step2["assessment"]
        print(f"\n✅ Present: {v.get('present')}")
        print(f"❌ Missing legal: {v.get('missing_legal')}")
        print(f"⚠️  Warnings: {v.get('warnings')}")
        print(f"\n⚖️  Compliant: {a.get('compliant')}   Risk: {a.get('risk_level')}")
        print(f"\n🎯 Suggested questions:")
        for q in step2["suggested_questions"]:
            print(f"   • {q}")

    elif cmd == "ask":
        if len(files) < 2:
            print("Usage: python -m features.ai.contract ask '<question>' <file1> [file2 ...]")
            sys.exit(1)
        question = files[0]
        sources = files[1:]
        step1 = extract_and_identify(sources)
        r = ask_contract(question, {"identification": step1["identification"]})
        print(f"\n💬 {r['answer']}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    _cli()