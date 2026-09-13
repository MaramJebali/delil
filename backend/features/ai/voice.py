"""
Voice — Speech-to-Text (STT) + Text-to-Speech (TTS) for Dalil.

STT  : faster-whisper (local, GPU/CPU)  →  Groq Whisper API (fallback)
TTS  : Microsoft Edge TTS (free, no compiler, Arabic + French neural voices)

Public API
──────────
    transcribe(audio_path, language=None)      → { text, lang, lang_probability, backend }
    synthesize(text, lang="fr", filename=None) → path to generated .mp3
    voice_answer(audio_path, actor, history, speak) → full voice loop (STT → agent → TTS)

CLI
───
    python -m features.ai.voice transcribe audio.wav
    python -m features.ai.voice speak "Bonjour, ici Dalil" --lang fr
    python -m features.ai.voice speak "مرحبا، هذا دليل" --lang ar
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")

AI_DIR = Path(__file__).resolve().parent
TTS_OUTPUT_DIR = AI_DIR / "tts_output"
TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Config ────────────────────────────────────────
STT_BACKEND        = os.getenv("STT_BACKEND", "whisper_local")      # whisper_local | groq
STT_WHISPER_MODEL  = os.getenv("STT_WHISPER_MODEL", "small")        # tiny|base|small|medium|large-v3
STT_DEVICE         = os.getenv("STT_DEVICE", "auto")                # auto|cuda|cpu
STT_GROQ_MODEL     = os.getenv("STT_GROQ_MODEL", "whisper-large-v3")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")

TTS_BACKEND        = os.getenv("TTS_BACKEND", "edge")               # edge
TTS_DEFAULT_LANG   = os.getenv("TTS_DEFAULT_LANG", "fr")            # fr | ar | en

# ── Edge TTS voices (Microsoft neural — free, no key) ──
EDGE_VOICES = {
    "fr": "fr-FR-DeniseNeural",         # French (France) — female
    "ar": "ar-EG-SalmaNeural",          # Arabic (Egypt)   — female
    "en": "en-US-AriaNeural",           # English (US)     — female
}

# Optional: different voice if you want male
#   fr: "fr-FR-HenriNeural"
#   ar: "ar-EG-ShakirNeural"
#   en: "en-US-GuyNeural"


# ═══════════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT  (STT)
# ═══════════════════════════════════════════════════════════════════

_whisper_singleton = None


def _get_whisper():
    global _whisper_singleton
    if _whisper_singleton is None:
        from faster_whisper import WhisperModel
        _whisper_singleton = WhisperModel(
            STT_WHISPER_MODEL,
            device=STT_DEVICE,
            compute_type="int8",
        )
    return _whisper_singleton


def _transcribe_local(audio_path: str, language: str | None = None) -> dict:
    """faster-whisper on GPU/CPU."""
    model = _get_whisper()
    segments, info = model.transcribe(audio_path, language=language)
    text = " ".join(s.text.strip() for s in segments).strip()
    return {
        "text": text,
        "lang": info.language,
        "lang_probability": float(info.language_probability) if info.language_probability else None,
        "backend": "faster-whisper",
    }


def _transcribe_groq(audio_path: str, language: str | None = None) -> dict:
    """Groq Whisper API (fallback — uses your GROQ_API_KEY)."""
    from openai import OpenAI
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
    with open(audio_path, "rb") as f:
        r = client.audio.transcriptions.create(
            model=STT_GROQ_MODEL,
            file=f,
            language=language if language else None,
        )
    return {
        "text": (r.text or "").strip(),
        "lang": language or "unknown",
        "lang_probability": None,
        "backend": "groq-whisper",
    }


def transcribe(audio_path: str, language: str | None = None) -> dict:
    """
    Audio file → { text, lang, lang_probability, backend }.

    Tries the configured backend first, falls back to the other.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(audio_path)

    # 1. Try primary backend
    if STT_BACKEND == "whisper_local":
        try:
            return _transcribe_local(audio_path, language)
        except Exception as e:
            print(f"⚠️  faster-whisper failed: {str(e)[:140]}")
            print("   Falling back to Groq Whisper API…")
    elif STT_BACKEND == "groq":
        try:
            return _transcribe_groq(audio_path, language)
        except Exception as e:
            print(f"⚠️  Groq Whisper failed: {str(e)[:140]}")
            print("   Falling back to local faster-whisper…")

    # 2. Fallback
    try:
        if STT_BACKEND == "whisper_local" and GROQ_API_KEY:
            return _transcribe_groq(audio_path, language)
        if STT_BACKEND == "groq":
            return _transcribe_local(audio_path, language)
    except Exception as e:
        print(f"❌ Fallback failed: {str(e)[:140]}")

    raise RuntimeError("No STT backend available.")


# ═══════════════════════════════════════════════════════════════════
#  TEXT-TO-SPEECH  (TTS) — Microsoft Edge TTS
# ═══════════════════════════════════════════════════════════════════

async def _edge_synth_async(text: str, voice: str, output_path: str) -> None:
    """Async Edge TTS call."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _synth_edge(text: str, lang: str, output_path: str) -> str:
    """
    Edge TTS — free, no key, no compile.
    Produces an .mp3 file (browser plays it directly).
    """
    voice = EDGE_VOICES.get(lang, EDGE_VOICES["fr"])
    # edge-tts always saves MP3 — force the .mp3 extension
    mp3_path = output_path.rsplit(".", 1)[0] + ".mp3"
    asyncio.run(_edge_synth_async(text, voice, mp3_path))
    return mp3_path


def synthesize(text: str, lang: str = TTS_DEFAULT_LANG, filename: str | None = None) -> str:
    """
    Text → path to generated audio file (.mp3).
    lang: 'fr' | 'ar' | 'en'
    """
    if not text or not text.strip():
        raise ValueError("Empty text")

    if filename is None:
        filename = f"dalil_{lang}_{int(time.time() * 1000)}.mp3"
    output_path = str(TTS_OUTPUT_DIR / filename)

    if TTS_BACKEND == "edge":
        try:
            return _synth_edge(text, lang, output_path)
        except Exception as e:
            print(f"⚠️  Edge TTS failed: {str(e)[:160]}")

    raise RuntimeError("No TTS backend available.")


# ═══════════════════════════════════════════════════════════════════
#  FULL VOICE LOOP  (STT → agent → TTS)
# ═══════════════════════════════════════════════════════════════════

def voice_answer(
    audio_path: str,
    actor: str,
    history: list | None = None,
    speak: bool = True,
) -> dict:
    """
    Complete voice pipeline for the Workflow Guidance feature.

    Steps:
      1. transcribe(audio)          → question
      2. agent.discuss(question)    → answer
      3. synthesize(answer)         → .mp3 (if speak=True)

    `actor` must be 'bailleur' or 'commercant'.
    """
    # Lazy import to avoid circular dependency (agent imports voice)
    from . import agent as _agent

    # 1. STT
    stt_result = transcribe(audio_path)
    question = stt_result["text"]
    print(f"🎤 Heard: {question}")

    # 2. LLM + RAG
    result = _agent.discuss(question, actor=actor, history=history or [])
    result["question"] = question
    result["stt_backend"] = stt_result["backend"]

    # 3. TTS
    if speak:
        try:
            out = synthesize(result["answer"], lang=result["lang"])
            result["audio_path"] = out
            print(f"🔊 Answer synthesized: {out}")
        except Exception as e:
            print(f"⚠️  TTS failed: {str(e)[:140]}")

    return result


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def _cli():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m features.ai.voice transcribe <audio.wav>")
        print("  python -m features.ai.voice speak '<text>' [--lang fr|ar|en]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "transcribe":
        if len(sys.argv) < 3:
            print("Provide an audio path.")
            sys.exit(1)
        path = sys.argv[2]
        print(f"🎤 Transcribing: {path}\n")
        r = transcribe(path)
        print(f"🌍 Language: {r['lang']}  (p={r['lang_probability']})")
        print(f"🔧 Backend:  {r['backend']}")
        print(f"\n📝 Text:\n{r['text']}")

    elif cmd == "speak":
        args = sys.argv[2:]
        if not args:
            print("Provide text to speak.")
            sys.exit(1)
        lang = TTS_DEFAULT_LANG
        if "--lang" in args:
            i = args.index("--lang")
            lang = args[i + 1]
            args = args[:i] + args[i + 2:]
        text = " ".join(args)
        print(f"🔊 Language: {lang}")
        print(f"📝 Text: {text}\n")
        out = synthesize(text, lang=lang)
        print(f"✅ Saved: {out}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    _cli()