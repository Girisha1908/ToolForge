# 🔨 ToolForge

**Turn API documentation into tools your AI agents can actually use.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)](backend/requirements.txt)

ToolForge is a universal API-to-agent adapter. Point it at an API's documentation — OpenAPI,
Swagger, Postman, or plain text/HTML — and it parses the API, generates agent-ready tool
definitions, and lets a Gemini-powered agent call those tools from natural language. No
hand-written integration required.

```
API Docs → Parse & Normalize → Generate Tools → Agent Selects Tool → Execute → Result
```

---

## ✨ What it does

- **Ingests** API docs from a URL or raw text — OpenAPI 3.x, Swagger 2.0, Postman collections, or
  unstructured HTML/text (with an LLM fallback parser for the latter).
- **Normalizes** every API into one common schema: endpoints, parameters, auth, request/response
  shapes.
- **Generates** deterministic, agent-ready tool definitions, with optional Gemini enrichment for
  better names/descriptions — enrichment is strictly validated and rejected wholesale if it
  invents endpoints or changes a method/path.
- **Executes** tools through a generic HTTP executor with SSRF-safe DNS resolution and connection
  pinning, redirect revalidation, and per-request auth injection.
- **Reasons** with a Gemini-backed agent loop (deterministic heuristic fallback when Gemini is
  unavailable) that picks the right tool from a natural-language prompt and returns a formatted
  answer.

## 🏗️ Architecture

```
Frontend (React)  →  Backend (FastAPI)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                   ▼
   API Parser        Tool Generator       Agent Runtime
        │                  │                   │
        └─────────► Normalized Spec ◄──────────┘
                           │
                           ▼
                    Tool Executor ──► External API
                           ▲
                       Gemini (reasoning + enrichment,
                       with deterministic fallbacks)
```

## 🛠️ Tech stack

| Layer      | Stack                                                  |
|------------|---------------------------------------------------------|
| Backend    | Python, FastAPI, httpx, Pydantic                         |
| Frontend   | React, Vite, Tailwind CSS                                |
| AI         | Google Gemini (`google-genai`)                           |
| Deployment | Docker, Docker Compose                                   |
| Testing    | `unittest` + FastAPI `TestClient`, 70+ backend tests      |

## 🚀 Quick Start

### Run with Docker (fastest)

Requires [Docker](https://docs.docker.com/get-docker/) with Compose.

```bash
git clone https://github.com/Girisha1908/ToolForge.git
cd ToolForge
cp .env.example .env   # fill in GEMINI_API_KEY and any other credentials you need
docker compose up --build
```

- Backend → `http://localhost:8000`
- Frontend → `http://localhost:5173`

> **Note:** `VITE_API_BASE_URL` is baked into the frontend at *build* time, not read at container
> startup. Set it in `.env` before running `docker compose up --build` — changing it afterwards
> requires `docker compose build frontend`, not just a restart.

Stop everything with `docker compose down`.

### Manual setup

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend** (in a separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 🧪 Testing

```bash
cd backend
python -m unittest discover -s tests
```

Covers SSRF protections, OpenAPI/Postman/text parsing, LLM-hallucination-guard fallbacks, tool
execution and authentication, agent tool-allowlisting, and the full HTTP route layer.

## 🔐 Security notes

- Outbound requests are SSRF-guarded: private/loopback/link-local/cloud-metadata IPs are blocked,
  DNS is resolved and pinned before connecting, and every redirect hop is revalidated.
- ToolForge's own API can optionally be gated behind a shared secret (`TOOLFORGE_API_KEY`); unset
  by default for local development.
- Third-party API credentials are configured once via server-side environment variables.
- Never commit `.env` — use `.env.example` as a template.

## 📌 Known limitations

- One global set of credentials is shared across all generated tools — no per-API/per-tenant
  credential scoping yet.
- The tool registry is in-memory and process-lifetime only — no persistence, no horizontal scaling.
- OAuth2-secured APIs are explicitly rejected rather than supported.
- The Docker setup here is local/dev-oriented, not production-hardened.

## 📜 License

MIT — see [LICENSE](LICENSE).

---

*Originally built for LatentForce BuildSprint 2026.*
