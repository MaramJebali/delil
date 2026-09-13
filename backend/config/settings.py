"""
Django settings for Dalil — Commercial Justice & Guidance platform.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Load .env  (CRITICAL — must come before any os.getenv call)
# ------------------------------------------------------------------
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------------
# Core
# ------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")

# ------------------------------------------------------------------
# Apps
# ------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",

    # Local
    "accounts",
    "features",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ------------------------------------------------------------------
# Password validation
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------
# i18n
# ------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Static / Media
# ------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# Custom user
# ------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ------------------------------------------------------------------
# DRF
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
CORS_ALLOW_CREDENTIALS = True

# ══════════════════════════════════════════════════════════════════
#  AI CONFIGURATION
# ══════════════════════════════════════════════════════════════════

# ── LLM Providers ────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

LLM_PRIMARY_PROVIDER = os.getenv("LLM_PRIMARY_PROVIDER", "groq")
LLM_PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "qwen/qwen3.8-27b")
LLM_FAST_MODEL = os.getenv("LLM_FAST_MODEL", "openai/gpt-oss-20b")
LLM_STRONG_MODEL = os.getenv("LLM_STRONG_MODEL", "openai/gpt-oss-120b")

LLM_FALLBACK_PROVIDER = os.getenv("LLM_FALLBACK_PROVIDER", "mistral")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "ministral-8b-latest")

# ── STT ──────────────────────────────────────────
STT_BACKEND = os.getenv("STT_BACKEND", "whisper_local")
STT_WHISPER_MODEL = os.getenv("STT_WHISPER_MODEL", "small")
STT_COHERE_MODEL = os.getenv(
    "STT_COHERE_MODEL", "CohereLabs/cohere-transcribe-arabic-07-2026"
)
STT_GROQ_MODEL = os.getenv("STT_GROQ_MODEL", "whisper-large-v3")
STT_DEVICE = os.getenv("STT_DEVICE", "auto")

# ── TTS ──────────────────────────────────────────
TTS_BACKEND = os.getenv("TTS_BACKEND", "silma")
TTS_SILMA_MODEL = os.getenv("TTS_SILMA_MODEL", "silma-ai/silma-tts")
TTS_MAGPIE_MODEL = os.getenv(
    "TTS_MAGPIE_MODEL", "nvidia/magpie_tts_multilingual_357m"
)
TTS_DEFAULT_LANG = os.getenv("TTS_DEFAULT_LANG", "en")
TTS_DEVICE = os.getenv("TTS_DEVICE", "auto")

# ── VLM (Contract / document extraction) ─────────
VLM_BACKEND = os.getenv("VLM_BACKEND", "local")
VLM_MODEL_PATH = os.getenv("VLM_MODEL_PATH", "")
VLM_DEVICE = os.getenv("VLM_DEVICE", "auto")