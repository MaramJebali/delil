<p align="center">
  <img src="./frontend/src/assets/LOGO.png" alt="Dalil logo" width="160">
</p>

<h1 align="center">Dalil (دليل)</h1>
<p align="center"><b>Platforme pour une guide juridique pour le droit commercial tunisien</b></p>

---

Dalil est une plateforme d'assistance juridique pour les PME tunisiennes.
Elle couvre deux cas d'usage autour du **fonds de commerce** (الأصل التجاري) :

1. **Compréhension du contrat** — analyse d'un contrat téléversé (PDF / image), extraction des champs, contrôle de conformité RNE / Code de Commerce.
2. **Accompagnement procédural** — assistant Rag conversationnel qui guide l'utilisateur à travers les procédures (bailleur vs commerçant), avec un diagramme d'étapes, des fiches d'avocats, et un squelette de contrat.


**Périmètre légal :** Loi n° 77-37 du 25 mai 1977 (baux commerciaux) et Code de Commerce — Livre II (fonds de commerce).

---

## Sommaire

- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Structure du projet](#structure-du-projet)
- [Prérequis](#prérequis)
- [Variables d'environnement](#variables-denvironnement)
- [Fichiers de données (non versionnés)](#fichiers-de-données-non-versionnés)
- [Comment lancer le projet](#comment-lancer-le-projet)
- [Endpoints API](#endpoints-api)
- [Modèles IA utilisés](#modèles-ia-utilisés)
- [Sources des données juridiques](#sources-des-données-juridiques)
- [Notes et limites](#notes-et-limites)
- [Licence](#licence)

---

## Architecture

```
┌─────────────────────────┐       ┌───────────────────────────────────┐
│  Frontend (React/Vite)  │──────▶│   Backend (Django REST Framework)  │
│  - Dashboard             │ HTTP  │  - Auth JWT                        │
│  - Contract Understanding│       │  - Feature endpoints               │
│  - Workflow Guidance     │       │  - AI pipeline (features/ai/)      │
└─────────────────────────┘       └──────────────┬──────────────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────────┐
                        ▼                          ▼                          ▼
                ┌───────────────┐        ┌───────────────────┐      ┌────────────────┐
                │    ChromaDB    │        │    Cloud LLMs      │      │   Local VLM     │
                │    (RAG)       │        │ Groq / Mistral /   │      │   MinerU        │
                │    e5-base     │        │ Gemini             │      │   Qwen2-VL      │
                └───────────────┘        └───────────────────┘      └────────────────┘
```

### Pipeline IA — Compréhension du contrat (2 étapes)

1. **Extraction + Identification**
   - VLM / OCR → markdown (cascade : Gemini Flash → Mistral Pixtral → MinerU local → Tesseract)
   - LLM texte → champs structurés (JSON)
   - Contrôle de conformité RNE (checklist par type de contrat)

2. **Analyse + Explication**
   - RAG sur la base vectorielle (ChromaDB + embeddings multilingues)
   - LLM → évaluation, risques, explications par acteur, questions suggérées
   - Post-checks : scrubber de termes français + vérification des articles cités

### Pipeline IA — Workflow Guidance (3 phases)

1. Intro (FR) + choix du rôle (bailleur / commerçant)
2. Confirmation + invitation à décrire la situation
3. Discussion conversationnelle :
   - Détection d'intention (LLM pour « avocats », mots-clés pour « workflow » / « contrat »)
   - Outils : `find_lawyers`, `generate_workflow_steps` (+ vérification contre le RAG), `generate_contract_format`
   - Réponse en 3 mouvements : accusé de réception, cœur de la réponse, prochaine étape

---

## Stack technique

### Backend

| Couche | Technologie |
|---|---|
| Framework | Django 6.x + Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Base vectorielle | ChromaDB (persistante, locale) |
| Embeddings | `intfloat/multilingual-e5-base` (via `sentence-transformers`, device CPU par défaut) |
| VLM local | MinerU (`Qwen2-VL-1.2B`, via `transformers` + `mineru-vl-utils`) |
| OCR local | Tesseract *(optionnel)* |
| PDF | PyMuPDF (`fitz`) |
| Images | Pillow |
| LLM texte | Groq (OpenAI-compatible) → Mistral (fallback) |
| VLM cloud | Gemini 1.5 Flash (REST) · Mistral Pixtral · Groq vision *(désactivé par défaut)* |

### Frontend

| Couche | Technologie |
|---|---|
| Framework | React 18 + Vite |
| Routing | React Router v6 |
| Animation | Framer Motion |
| Icônes | Lucide React |
| HTTP | Axios (instance partagée `api`) |
| Style | Tailwind CSS |
| Palette | `#050B16` (navy) · `#FAF7F0` (cream) · `#E8C766` (gold) |

---

## Structure du projet

```
Delil/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                        # ⚠️ NON versionné — à créer
│   ├── api/                        # Projet Django
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── ...
│   └── features/                   # App principale
│       ├── __init__.py
│       ├── views.py                # Vues DRF (Contract + Workflow)
│       ├── urls.py
│       ├── models.py
│       ├── apps.py
│       └── ai/
│           ├── __init__.py
│           ├── agent.py            # Workflow Guidance (3 phases)
│           ├── contract.py         # Contract Understanding (2 étapes)
│           ├── tools.py            # Outils partagés (workflow, lawyers, contrat)
│           ├── rag.py              # ChromaDB : build + query
│           ├── voice.py            # STT (Whisper) + TTS
│           ├── data/               # ⚠️ NON$versionné — voir section dédiée
│           │   ├── advocates.json
│           │   ├── code_comm.json
│           │   ├── contract_requirements.json
│           │   └── loi_77_37.json
│           └── chroma_db/          # ⚠️ NON versionné — régénéré par `rag build`
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/
        │   └── axios.js             # Instance Axios + intercepteur JWT
        ├── context/
        │   └── AuthContext.jsx
        ├── assets/
        │   ├── hero.jpg              # ⚠️ NON versionné
        │   └── logo.png              # ⚠️ NON versionné
        └── routes/
            ├── Dashboard.jsx
            ├── Login.jsx
            ├── Register.jsx
            └── features/
                ├── ContractUnderstanding.jsx
                ├── WorkflowGuidance.jsx
                └── DisputeResolution.jsx   # stub
```

---

## Prérequis

| Outil | Version min. | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 testé |
| Node.js | 18+ | LTS recommandé |
| npm / pnpm / yarn | — | au choix |
| Git | — | — |
| GPU CUDA *(optionnel)* | 12.x | Requis pour le VLM local MinerU (fallback) |
| Tesseract OCR *(optionnel)* | 5.x | Fallback OCR local |

---

## Variables d'environnement

Créer `backend/.env` (non versionné) :

```env
# ─── Django ───────────────────────────────────────────────────
SECRET_KEY=change-me-in-production
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1

# ─── Auth JWT ─────────────────────────────────────────────────
JWT_SIGNING_KEY=use-a-32-char-random-string-here
JWT_ACCESS_LIFETIME_MIN=60
JWT_REFRESH_LIFETIME_DAYS=7

# ─── LLM — Groq (primaire pour le texte) ──────────────────────
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_PRIMARY_MODEL=openai/gpt-oss-20b
LLM_STRONG_MODEL=openai/gpt-oss-20b
LLM_FAST_MODEL=openai/gpt-oss-20b
LLM_FALLBACK_MODEL=ministral-8b-latest

# ─── LLM — Mistral (fallback texte + VLM image) ───────────────
MISTRAL_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ─── VLM — Google Gemini (OCR rapide) ─────────────────────────
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ─── VLM — cascade OCR ────────────────────────────────────────
USE_CLOUD_VLM=1
USE_GROQ_VISION=0
CLOUD_VLM_MAX_DIM=1600
CLOUD_VLM_JPEG_Q=88
MISTRAL_VISION_MODEL=pixtral-12b-2409
GEMINI_VISION_MODEL=gemini-1.5-flash
VLM_MAX_PAGES=8

# ─── VLM local MinerU (fallback privé, nécessite GPU) ─────────
VLM_MODEL_PATH=C:\Users\<you>\...\models\MinerU2.5-Pro-2605-1.2B
VLM_DEVICE=auto
VLM_DPI_SCALE=2.0

# ─── Embeddings (RAG) ─────────────────────────────────────────
EMBEDDING_MODEL=intfloat/multilingual-e5-base
EMBEDDING_DEVICE=cpu

# ─── Tesseract (optionnel) ────────────────────────────────────
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Où obtenir les clés

| Clé | Fournisseur | URL |
|---|---|---|
| `GROQ_API_KEY` | Groq Cloud | https://console.groq.com/keys |
| `MISTRAL_API_KEY` | Mistral AI | https://console.mistral.ai/api-keys/ |
| `GEMINI_API_KEY` | Google AI Studio | https://aistudio.google.com/app/apikey |

---

## Fichiers de données (non versionnés)

Ces fichiers ne sont pas poussés sur Git (voir `.gitignore`) car ils contiennent des données personnelles ou volumineuses. Ils doivent être placés manuellement dans `backend/features/ai/data/`.

### `advocates.json` — annuaire d'avocats

Base interne des avocats tunisiens, filtrée par région.

```json
{
  "advocates": {
    "all_regions": [
      {
        "id": 1,
        "full_name": "آمنة الصغير",
        "address": "نهج بحيرة ليمان اقامة 2001 ب س 34",
        "phone_numbers": ["71964633", "94975741"],
        "primary_court": "تونس",
        "region": "تونس",
        "tableau": "تعقيب"
      }
    ]
  }
}
```

Utilisé par l'outil `find_lawyers()` (Workflow Guidance) pour proposer des avocats en fonction de la région détectée dans la question.

### `code_comm.json` — Code de Commerce (Livre II) Bases de données scrappées avant la transformation en vector database

Articles 189 à 467 relatifs au fonds de commerce.
Structure : `{ "code_de_commerce": { "articles": [ {...}, ... ] } }`

### `loi_77_37.json` — Loi 77-37 sur les baux commerciaux -Bases de données scrappées avant la transformation en vector database

Articles 1 à 35 relatifs aux rapports bailleurs / locataires.
Structure : `{ "loi_77_37": { "articles": [ {...}, ... ] } }`

### `contract_requirements.json` — Checklists RNE

Contient, par type de contrat, la liste des mentions obligatoires (identité des parties, CIN, description du fonds, clauses obligatoires, avocat rédacteur, signatures, etc.), avec sévérité (`blocking` / `warning`) et base légale.

Structure :

```json
{
  "contract_types": {
    "location-gerance": { "mandatory_items": [ ] },
    "bail-commercial": { "mandatory_items": [ ] },
    "cession-fonds-commerce": { "mandatory_items": [ ] }
  }
}
```

### `chroma_db/` — base vectorielle Chroma

Générée à partir des deux JSON juridiques par :

```bash
python -m features.ai.rag build
```

Contient un embedding par (article × section × langue).

- **Sections :** `summary`, `conditions`, `consequences`, `delais`, `keywords`, `related`
- **Langues :** `fr`, `ar`

### `frontend/src/assets/hero.jpg`

Image de fond du Dashboard. Fournir un JPG de ~2000×1200 min.

### `frontend/src/assets/logo.png`

Logo de l'application, utilisé dans ce README et dans l'en-tête du Dashboard.

---

## Comment lancer le projet

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

Créer `backend/.env` (voir section précédente), puis placer les 4 JSON dans `backend/features/ai/data/`, puis :

```bash
# Construire la base vectorielle (une seule fois)
python -m features.ai.rag build

# Migrations + lancement
python manage.py migrate
python manage.py runserver
```

Backend disponible sur `http://127.0.0.1:8000/`

> **Astuce dev :** si vous n'avez pas de GPU, laissez `VLM_DEVICE=cpu` et `USE_CLOUD_VLM=1` — les VLM cloud feront tout le travail OCR. MinerU local ne sera utilisé que si tout le cloud échoue.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible sur `http://127.0.0.1:5173/`

Vérifier que `src/api/axios.js` pointe vers le backend :

```js
baseURL: "http://127.0.0.1:8000/api",
```

### 3. Vérifier que le RAG répond

```bash
cd backend
python -m features.ai.rag query "renouvellement du bail commercial"
python -m features.ai.rag stats
```

Attendu : au moins 6 chunks retournés avec articles `loi77_37_art*` ou `codecommerce_art*`.

### 4. Tester un contrat en CLI

```bash
cd backend
python -m features.ai.contract extract path/to/contrat.pdf --json
python -m features.ai.contract analyze path/to/contrat.pdf
python -m features.ai.contract ask "Quelles sont les formalités obligatoires ?" path/to/contrat.pdf
```

---

## Endpoints API

Préfixe : `/api/`

### Feature 1 — Contract Understanding

| Méthode | Route | Description |
|---|---|---|
| POST | `/features/contract/extract/` | Étape 1 : upload → champs + checklist RNE |
| POST | `/features/contract/analyze/` | Étape 2 : analyse complète après validation |
| POST | `/features/contract/ask/` | Q&A sur le contrat analysé |

### Feature 2 — Workflow Guidance

| Méthode | Route | Description |
|---|---|---|
| POST | `/features/workflow/intro/` | Phase 1 : message d'accueil + 2 choix |
| POST | `/features/workflow/choose-actor/` | Phase 2 : confirmation + invitation |
| POST | `/features/workflow/discuss/` | Phase 3 : discussion (RAG + LLM + outils) |
| POST | `/features/workflow/stt/` | Audio → texte |
| POST | `/features/workflow/tts/` | Texte → audio `.mp3` |

### Feature 3 — Dispute Resolution

| Méthode | Route | Description |
|---|---|---|
| POST | `/features/dispute/resolve/` | *(501 — non implémenté)* |

> Tous les endpoints nécessitent un header `Authorization: Bearer <JWT>`.

---

## Modèles IA utilisés

### LLM texte (raisonnement, structuration, analyse)

| Usage | Modèle par défaut | Fournisseur |
|---|---|---|
| Primaire | `openai/gpt-oss-20b` | Groq |
| Fort (structuration contrats) | `openai/gpt-oss-20b` | Groq |
| Rapide (classif., intent, langue) | `openai/gpt-oss-20b` | Groq |
| Fallback | `ministral-8b-latest` | Mistral |

Tous les modèles sont interchangeables via `.env` — l'API Groq est OpenAI-compatible, donc on peut basculer sur `qwen/qwen3.8-27b` ou `openai/gpt-oss-120b` sans changer une ligne de code.

### VLM / OCR (extraction depuis images et PDF scannés)

Cascade dans l'ordre, s'arrête au premier qui réussit :

| Ordre | Modèle | Fournisseur | Latence | Notes |
|---|---|---|---|---|
| 1 | Llama 4 Scout vision *(désactivé)* | Groq | — | Off par défaut (pas de modèle vision sur le compte actuel) |
| 2 | `gemini-1.5-flash` | Google | 2–4 s | Excellent sur FR + AR |
| 3 | `pixtral-12b-2409` | Mistral | 5–10 s | Fort sur le juridique FR/AR |
| 4 | Qwen2-VL-1.2B (MinerU) | Local (GPU) | 20–40 s | 100% privé, nécessite CUDA |
| 5 | Tesseract 5 | Local | 1–3 s | Optionnel, langue `fra+ara` |

### Embeddings (RAG)

| Modèle | Dimension | Device |
|---|---|---|
| `intfloat/multilingual-e5-base` | 768 | CPU (par défaut) |

Basculer sur GPU via `EMBEDDING_DEVICE=cuda` dans `.env` (recommandé seulement avec PyTorch ≥ 2.5 + CUDA ≥ 12.8).

### STT / TTS (`voice.py`)

- **STT :** Whisper (Groq `whisper-large-v3-turbo`)
- **TTS :** moteur local (voir `features/ai/voice.py`)

---

## Sources des données juridiques

| Source | Référence | Fichier |
|---|---|---|
| Loi 77-37 | JORT n° 38 du 31 mai – 3 juin 1977 | `loi_77_37.json` |
| Code de Commerce, Livre II | Loi n° 59-129 du 5 octobre 1959, modifiée | `code_comm.json` |
| Loi 95-44 | Registre National des Entreprises (RNE) | *(intégré dans `contract_requirements.json`)* |
| Annuaire d'avocats | Base interne | `advocates.json` |
| Checklists RNE | Consolidation interne | `contract_requirements.json` |

Chaque article dans le RAG est indexé sous plusieurs sections : `summary`, `conditions`, `consequences`, `delais`, `keywords`, `related`. Chaque section existe en français et en arabe, ce qui permet au retriever de suivre la langue de la question.

---

## Notes et limites

- **Données personnelles** — les contrats contiennent des CIN, adresses, signatures. Si vous activez `USE_CLOUD_VLM=1`, ces données sont envoyées à Google / Mistral. Pour un déploiement en cabinet d'avocats, la conformité à la loi 2004-63 (protection des données personnelles) doit être vérifiée, et l'accord du client obtenu avant tout transfert.

- **Modèles en évolution** — Groq et Mistral retirent régulièrement des modèles. Si un modèle disparaît, changer la valeur dans `.env`. La liste Groq s'obtient via :

  ```bash
  python -c "from openai import OpenAI; import os; from dotenv import load_dotenv; \
  load_dotenv(); c=OpenAI(base_url='https://api.groq.com/openai/v1', \
  api_key=os.getenv('GROQ_API_KEY')); [print(m.id) for m in c.models.list().data]"
  ```

- **Hallucinations** — les prompts forcent le LLM à ne citer que les articles présents dans le contexte RAG. Un post-check (`_verify_analysis_articles`) supprime toute référence à un article non retrouvé.

- **Terminologie** — un scrubber (`_scrub_frenchism`) remplace les termes français de France (BODACC, Kbis, RCS) par leurs équivalents tunisiens (JORT, Extrait RNE, RNE) avant d'envoyer la réponse au frontend.

- **Langue de sortie** — Contract Understanding répond uniquement en français, quelle que soit la langue de la question. L'OCR en revanche préserve la langue d'origine du document (FR ou AR).

---
## 🏆 Contexte — Hack4Justice 2026 (Track B)
 
Ce projet est une **solution proposée dans le cadre du **Hack4Justice**, organisé par **HiiL (Hague Institute for Innovation of Law)**, pour sa **4ème édition**, sur le **Challenge B — Digital Dispute Resolution & Pre-Litigation**.
 
 
Le **Challenge B** porte spécifiquement sur la résolution digitale des litiges et la pré-contentieux : aider les mSME à collecter des preuves, automatiser les mises en demeure, et constituer des dossiers de réclamation structurés pour une résolution rapide via médiation numérique ou traitement judiciaire accéléré — avec un module institutionnel obligatoire destiné aux greffiers, médiateurs ou arbitres.
 
---
Projet interne — Tunisia / Dalil.