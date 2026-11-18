# CodeSage – AI Software Development Intelligence

[![Docker Compose](https://img.shields.io/badge/docker--compose-ready-blue.svg)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![MySQL 8.x](https://img.shields.io/badge/MySQL-8.x_ONLY-4479A1.svg)](backend/init.sql)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](frontend/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](frontend/tailwind.config.js)

An advanced 5-credit CSE major project full-stack platform delivering comprehensive codebase intelligence, RAG-grounded chat with citation validation, static and AI code diagnostics, codebase-derived interview simulations, architecture documentation generation, and developer analytics.

---

## 1. Architectural Highlights & Strict Constraints

| Layer | Implementation | Constraints & Guarantees |
| :--- | :--- | :--- |
| **Database** | **MySQL 8.x ONLY** | **Strictly prohibited**: Mongo, Postgres, SQLite, Redis, Pinecone, Chroma, Qdrant, Supabase. All application data, embeddings, and jobs reside exclusively in MySQL. |
| **Embeddings & Search** | Sentence Transformers (`all-MiniLM-L6-v2`) + MySQL Vector BLOBs | Stored as binary float32 blobs in MySQL (`code_embeddings`). Application-side cosine similarity combined with full-text/keyword matching (70% semantic + 30% lexical re-ranking). |
| **Job Queue** | Custom MySQL-backed Task Queue | Zero Redis/Celery dependencies. Employs `SELECT ... FOR UPDATE (skip_locked=True)`, exponential backoff retries, heartbeat recovery of stale jobs, and idempotency keys. |
| **Parsers** | Python AST, Regex/Tree-sitter | Supported languages: Python, JavaScript, TypeScript, Java (No C/C++). Single-file parse failures never fail repository ingestion. |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand | CodeMirror 6 (code inspection), Recharts (analytics), React Flow (interactive dependency graph). |

---

## 2. Core Modules

```
                    ┌────────────────────────────────────────────────────────┐
                    │               CodeSage Intelligence Hub               │
                    └───────────────────────────┬────────────────────────────┘
                                                │
         ┌───────────────────┬──────────────────┼───────────────────┬───────────────────┐
         ▼                   ▼                  ▼                   ▼                   ▼
   ┌───────────┐       ┌───────────┐      ┌───────────┐       ┌───────────┐       ┌───────────┐
   │ Module 1  │       │ Module 2  │      │ Module 3  │       │ Module 4  │       │ Module 5  │
   │ Ingestion │       │ RAG Code  │      │ AI Code   │       │ Interview │       │ Docs &    │
   │ & Parsing │       │ Assistant │      │ Review    │       │ Engine    │       │ Arch Gen  │
   └───────────┘       └───────────┘      └───────────┘       └───────────┘       └───────────┘
```

1. **Repository Ingestion & Intelligence Engine**: Safe ZIP extraction with zip-slip path traversal and decompression bomb defense; public/private GitHub import; immutable version snapshots; multi-language AST parsing; NetworkX dependency graphs.
2. **RAG Code Intelligence Assistant**: Syntax-aware code chunking; hybrid search; LLM synthesis with **mandatory citation validation** (`[file_path:L<start>-L<end>]`); prompt injection defenses.
3. **AI Code Review & Security Diagnostics**: Hybrid deterministic checks (hardcoded secrets, SQL injection heuristics, extreme cyclomatic complexity >20, code smells) combined with AI explanations; verified defect vs. recommendation status tracking.
4. **Repository-Based Interview Intelligence**: Codebase-grounded technical interview questions; adaptive difficulty; standardized rubric grading (correctness, depth, repo understanding); scorecard with topic mastery and revision guides.
5. **Documentation & Architecture Generator**: Automatic Markdown documentation from real code evidence (README, Architecture Topology with Mermaid diagrams, API specs, DB schema summaries).
6. **Developer Analytics Dashboard**: Objective AST measurements (LOC, language breakdown, cyclomatic complexity distributions, circular dependency cycles).

---

## 3. Quickstart with Docker Compose

Ensure Docker and Docker Compose are installed.

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Build and launch all containers (MySQL 8, Backend, Worker, Frontend)
docker-compose up --build
```

Services will be accessible at:
- **Frontend Web UI:** `http://localhost:5173`
- **FastAPI Interactive Docs:** `http://localhost:8000/api/docs`
- **MySQL 8.0:** `localhost:3306`

---

## 4. Local Development Setup

### Backend & Background Worker
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal, start the MySQL background worker
python -m app.workers.runner
```

### Frontend
```bash
cd frontend
pnpm install # or npm install
pnpm dev     # or npm run dev
```

---

## 5. Running the Test Suites

### Backend Pytest Suite
```bash
cd backend
pytest tests/ -v
```

### Frontend Vitest Suite
```bash
cd frontend
pnpm test
```
