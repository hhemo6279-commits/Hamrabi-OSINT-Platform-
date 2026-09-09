# Hamrabi — Intelligent OSINT Platform

AI-assisted OSINT investigation & correlation platform.
Legal / academic use only. Collects and correlates **public, authorised**
information from open sources (DNS, WHOIS, TLS certificates, public HTTP
metadata, public profiles). It does **not** attack, bypass protections, or
access private accounts.

## Architecture

```
input ── text / username / email / domain / ip / url / image ──► Image OCR
        │                                                             │
        ▼                                                             ▼
Input Manager ──► Entity Extraction ◄────────── embedded text + indicators
        │
        ▼
OSINT Connectors (DNS · WHOIS · Certificate · HTTP/fingerprint ·
                  Certificate-Transparency subdomains · public profiles)
        │
        ▼                 ┌─────────────────────────────┐
Evidence-Based Confidence ─►  Correlation Engine       │
Engine                         (entity graph)          │
        │                          ▲                   │
        ▼                          │                   ▼
 AI Analysis (summary · classify · explain ─ evidence-grounded)
        │
        ▼
 Dashboard · Graph View · PDF Report (AI section + Timeline)
```

## Backend modules
| Path | Purpose |
| --- | --- |
| `app/modules/input_manager.py` | auto-classifies + sanitizes input |
| `app/modules/entity_extraction.py` | extracts IPs, emails, domains, URLs, usernames |
| `app/modules/ocr.py` | OCR + EXIF/metadata extraction, magic-byte validation |
| `app/modules/confidence.py` | deterministic evidence-based confidence rules |
| `app/modules/correlation.py` | entity graph engine (email→domain, domain→IP, …, expansion) |
| `app/connectors/` | one file per source, unified result schema |
| `app/services/pipeline.py` | orchestration + domain→IP expansion |
| `app/services/ai.py` | provider-agnostic AI (OpenAI/Anthropic) + offline fallback |
| `app/services/report.py` | PDF report (executive summary, findings, sources, graph, timeline, AI) |
| `app/core/limiter.py` | in-memory rate limiter middleware |
| `app/core/config.py` | env-driven settings (secret, CORS, TTL) |
| `tests/` | pytest suite: auth, security, validation, pipeline, expansion |

## Frontend pages
- **Dashboard** — list of investigations
- **New Investigation** — text/indicator input + image upload (OCR/EXIF)
- **Results** — entities, findings/evidence, correlations, AI analysis button
- **Entity View** — per-entity evidence + correlations (`/inv/:id/entity/:eid`)
- **Sources** — evidence table Source / Timestamp / Query / Result / Confidence
- **Graph View** — interactive correlation graph

## Docker
```bash
docker compose up --build        # backend :8000  frontend :5173
```

## Requirements
- Python 3.11+ (`py` on Windows)
- Node.js 18+
- Docker (optional, for containers)

## Running in dev

### 1. Backend
```powershell
py -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python backend\run.py     # serves on http://127.0.0.1:8000
```
or with uvicorn directly:
```powershell
uvicorn app.main:app --app-dir backend --port 8000
```
API docs: http://127.0.0.1:8000/docs

### 2. Frontend
```powershell
cd frontend
npm install
npm run dev        # -> http://127.0.0.1:5173 (proxies /api to :8000)
```

### 3. Sanity check (optional)
```powershell
backend\.venv\Scripts\python backend\sanity_check.py
```

### 4. Tests (phase 10 checklist)
```powershell
backend\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
backend\.venv\Scripts\python -m pytest backend\tests -q
```
Covers: authentication, access control, input validation, XSS/CRLF
sanitization, upload validation, rate limiting, evidence-based confidence,
entity extraction and correlation.

## Optional extras
- **PDF reports**: included via `requirements-dev.txt` (`reportlab`)
- **OCR**: `pip install pillow pytesseract` + install Tesseract engine
  (https://github.com/tesseract-ocr/tesseract)
- **Live AI**: set environment variables, then use the AI button in the
  UI (`Analyze with AI`) or `POST /api/investigations/{id}/ai`:

```powershell
set HAMRABI_AI_PROVIDER=openai
set OPENAI_API_KEY=sk-...        # or HAMRABI_AI_PROVIDER=anthropic + ANTHROPIC_API_KEY
```
All AI outputs run through a strict *evidence-grounded* system prompt and
fall back to a deterministic summarizer when no key is configured.

## Legal note
This platform is designed for **legitimate, lawful and academic** research on
*publicly available* data. Do not use it against systems or persons you are
not authorised to investigate.