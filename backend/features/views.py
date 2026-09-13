"""
Feature endpoints.

Feature 1 — Contract Understanding:
    /api/features/contract/extract/   → STEP 1: upload file(s), get fields + checklist
    /api/features/contract/analyze/   → STEP 2: after user validation, full analysis
    /api/features/contract/ask/       → Q&A about the analyzed contract

Feature 2 — Workflow Guidance:
    /api/features/workflow/intro/         → greeting + 2 actor choices
    /api/features/workflow/choose-actor/  → acknowledgment + invitation
    /api/features/workflow/discuss/       → RAG + LLM answer
    /api/features/workflow/stt/           → audio → text
    /api/features/workflow/tts/           → text  → audio (.mp3)
"""

import os
import tempfile
import traceback

from django.http import FileResponse
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


# ── Lazy imports (so Django boots without heavy AI deps) ──
def _agent():
    from .ai import agent as _a
    return _a


def _voice():
    from .ai import voice as _v
    return _v


def _contract():
    from .ai import contract as _c
    return _c


def _print_traceback(label: str, e: Exception):
    print("\n" + "=" * 70)
    print(f"❌ {label} failed: {type(e).__name__}: {e}")
    print("=" * 70)
    traceback.print_exc()
    print("=" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════
#  Feature 1 — Contract Understanding
# ═══════════════════════════════════════════════════════════════════

class ContractExtractView(APIView):
    """STEP 1 — Upload one or more files (PDF/images), get extracted fields + RNE checklist."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not files:
            return Response(
                {"detail": "No files uploaded. Send them under 'files' (multipart)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tmp_paths: list[str] = []
        try:
            for f in files:
                suffix = os.path.splitext(f.name or "")[1].lower() or ".bin"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    for chunk in f.chunks():
                        tmp.write(chunk)
                    tmp_paths.append(tmp.name)

            result = _contract().extract_and_identify(tmp_paths)
            return Response(result)

        except Exception as e:
            _print_traceback("ContractExtractView", e)
            return Response(
                {"detail": f"{type(e).__name__}: {str(e)[:500]}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            for p in tmp_paths:
                try:
                    os.unlink(p)
                except OSError:
                    pass


class ContractAnalyzeView(APIView):
    """STEP 2 — User-validated fields → full analysis + explanation + questions."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        identification = request.data.get("identification")
        completeness = request.data.get("completeness")

        if not identification or not isinstance(identification, dict):
            return Response({"detail": "Missing 'identification' object."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            result = _contract().analyze(identification, completeness=completeness)
            return Response(result)
        except Exception as e:
            _print_traceback("ContractAnalyzeView", e)
            return Response(
                {"detail": f"{type(e).__name__}: {str(e)[:500]}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ContractAskView(APIView):
    """Q&A — user asks about the analyzed contract."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        contract_context = request.data.get("contract_context") or {}
        history = request.data.get("history") or []

        if not question:
            return Response({"detail": "Missing 'question'."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not contract_context:
            return Response({"detail": "Missing 'contract_context'."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            result = _contract().ask_contract(question, contract_context, history=history)
            return Response(result)
        except Exception as e:
            _print_traceback("ContractAskView", e)
            return Response(
                {"detail": f"{type(e).__name__}: {str(e)[:500]}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ═══════════════════════════════════════════════════════════════════
#  Feature 2 — Workflow Guidance
# ═══════════════════════════════════════════════════════════════════

class WorkflowIntroView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            return Response(_agent().intro())
        except Exception as e:
            _print_traceback("WorkflowIntroView", e)
            return Response({"detail": str(e)[:250]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorkflowChooseActorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        actor = (request.data.get("actor") or "").strip()
        history = request.data.get("history") or []
        if actor not in ("bailleur", "commercant"):
            return Response({"detail": "Invalid actor."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(_agent().choose_actor(actor, history=history))
        except Exception as e:
            _print_traceback("WorkflowChooseActorView", e)
            return Response({"detail": str(e)[:250]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorkflowDiscussView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        actor = (request.data.get("actor") or "").strip()
        history = request.data.get("history") or []

        if not question or actor not in ("bailleur", "commercant"):
            return Response({"detail": "Missing question or actor."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(_agent().discuss(question, actor=actor, history=history))
        except Exception as e:
            _print_traceback("WorkflowDiscussView", e)
            return Response({"detail": str(e)[:250]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorkflowSTTView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        audio = request.FILES.get("audio")
        if not audio:
            return Response({"detail": "No audio file."},
                            status=status.HTTP_400_BAD_REQUEST)

        suffix = os.path.splitext(audio.name or "")[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            for chunk in audio.chunks():
                f.write(chunk)
            tmp_path = f.name

        try:
            result = _voice().transcribe(tmp_path)
            return Response(result)
        except Exception as e:
            _print_traceback("WorkflowSTTView", e)
            return Response({"detail": str(e)[:250]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


class WorkflowTTSView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        lang = (request.data.get("lang") or "fr").strip()
        if not text:
            return Response({"detail": "Empty text."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            path = _voice().synthesize(text, lang=lang)
            return FileResponse(open(path, "rb"), content_type="audio/mpeg")
        except Exception as e:
            _print_traceback("WorkflowTTSView", e)
            return Response({"detail": str(e)[:250]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ═══════════════════════════════════════════════════════════════════
#  Feature 3 — Dispute Resolution (stub)
# ═══════════════════════════════════════════════════════════════════

class DisputeResolveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return Response(
            {"detail": "Dispute resolution not implemented yet."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )