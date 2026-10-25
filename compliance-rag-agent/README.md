# Engineering Compliance RAG System (`compliance-rag-agent`)

An enterprise-grade, modular Regulatory & Engineering Compliance Verification Agent built with **Django 5.x REST Framework (DRF)**, **ChromaDB**, **LangChain Core**, **Pydantic v2**, and a **React 18+ Progressive Web App (PWA)** styled with TailwindCSS.

Designed for auditing engineering designs, manufacturing specs, and operational procedures against regulatory standards such as **ISO 9001:2015**, **ASME BPVC Section VIII**, and **IEC 61508 Functional Safety**.

---

## 🏗️ Architecture & Technology Stack

| Layer | Technologies | Description |
|---|---|---|
| **Backend** | Python 3.11, Django 5.x, DRF | High-throughput REST API with clean modular apps layout (`apps.rag`). |
| **Vector Database** | ChromaDB (`chromadb>=0.5.0`) | Persistent vector store volume (`chroma_data`) with Cosine similarity indexing. |
| **AI Orchestration** | LangChain Core, Pydantic v2 | Strict schema validation, prompt templates, and structured compliance audit synthesis. |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) | Django ORM for standards metadata, document management, and compliance audit logging. |
| **Frontend** | React 18, Vite, TypeScript | Modern mobile-first PWA with Lucide icons, Axios, and TailwindCSS glassmorphism. |
| **Native Ready** | Capacitor & Electron Compatible | Structured with `viewport-fit=cover`, safe-area insets, and `capacitor.config.ts`. |
| **Containerization** | Docker & Docker Compose | Multi-container setup with dedicated volumes for vector and database persistence. |

---

## 📂 Repository Layout

```text
compliance-rag-agent/
├── .env.example                # Canonical environment variable specifications
├── .gitignore                  # Git exclusions for Python, Node, Chroma, and builds
├── docker-compose.yml          # Container definitions for backend, frontend & volumes
├── Dockerfile.backend          # Python 3.11 slim multi-stage container
├── Dockerfile.frontend         # Node 20 alpine Vite dev & Nginx production container
├── requirements.txt            # Python dependencies (Django 5, DRF, ChromaDB, etc.)
├── README.md                   # System documentation and operational runbook
│
├── backend/                    # Django 5.x REST Framework Backend
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                 # Project root settings & URL routing
│   │   ├── __init__.py
│   │   ├── settings.py         # CORS, DB switch, ChromaDB paths, DRF configs
│   │   ├── urls.py             # Route delegator (/admin/, /api/rag/)
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/
│       ├── __init__.py
│       └── rag/                # Modular Compliance RAG App
│           ├── __init__.py
│           ├── admin.py        # Django Admin configuration
│           ├── apps.py
│           ├── models.py       # ComplianceStandard, ComplianceDocument, ComplianceAuditLog
│           ├── schemas.py      # Pydantic v2 validation schemas
│           ├── serializers.py  # DRF ModelSerializers
│           ├── urls.py         # API endpoints (/query/, /ingest/, /health/, etc.)
│           ├── views.py        # DRF APIViews
│           └── services/
│               ├── __init__.py
│               ├── chroma.py      # Persistent ChromaDB client singleton
│               ├── ingestion.py   # Clause-aware chunking & standard seeding
│               └── rag_engine.py  # LangChain prompt orchestration & audit synthesis
│
└── frontend/                   # React 18+ (Vite, TailwindCSS, PWA)
    ├── package.json
    ├── vite.config.ts          # Vite configuration with PWA plugin & API proxy
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── tailwind.config.js      # Dark mode slate & emerald engineering color tokens
    ├── postcss.config.js
    ├── index.html              # PWA manifest & mobile-first meta tags
    ├── capacitor.config.ts     # Mobile packaging configuration
    ├── public/
    │   ├── manifest.json       # Web App Manifest
    │   └── favicon.svg         # SVG vector shield icon
    └── src/
        ├── main.tsx            # React DOM mounting & ServiceWorker registration
        ├── App.tsx             # Interactive Compliance Verification Dashboard
        ├── index.css           # Tailwind directives & glassmorphism primitives
        ├── types/              # TypeScript interfaces mirroring Pydantic models
        ├── services/
        │   └── api.ts          # Axios API client configured for backend proxy
        └── components/
            ├── Header.tsx              # System diagnostics & action triggers
            ├── ComplianceBadge.tsx     # Dynamic verdict indicators
            ├── CitationCard.tsx        # Clause citations & snippet cards
            ├── DocumentIngestModal.tsx # Vector store document upload modal
            └── AuditTrailPanel.tsx     # Historical audit trail drawer
```

---

## 🚀 Quickstart with Docker Compose

Spin up the entire stack with persistent vector and relational storage:

```bash
# 1. Navigate into repository
cd compliance-rag-agent

# 2. Build and start services
docker compose up --build
```

- **Frontend Application**: [http://localhost:5173](http://localhost:5173)
- **Django REST API**: [http://localhost:8000/api/rag/health/](http://localhost:8000/api/rag/health/)
- **Django Admin**: [http://localhost:8000/admin/](http://localhost:8000/admin/)

Persistent storage is automatically created in named volumes:
- `compliance_rag_chroma_data` (`/app/chroma_data`)
- `compliance_rag_db_data` (`/app/db_data`)

---

## 💻 Local Development Setup (Without Docker)

### 1. Backend Setup (Python 3.11)

```bash
cd compliance-rag-agent/backend

# Create and activate virtual environment
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# (Optional) Seed sample engineering standards (ISO 9001, ASME Section VIII, IEC 61508)
# Can also be triggered directly from the UI "Seed Standards" button
curl -X POST http://127.0.0.1:8000/api/rag/seed/

# Launch development server
python manage.py runserver 127.0.0.1:8000
```

### 2. Frontend Setup (Node 20+)

```bash
cd compliance-rag-agent/frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The application will be accessible at [http://localhost:5173](http://localhost:5173).

---

## 🔒 CORS Configuration

CORS is configured via `django-cors-headers` in [backend/config/settings.py](file:///backend/config/settings.py):
- `corsheaders.middleware.CorsMiddleware` is registered at the top of `MIDDLEWARE`.
- In `DEBUG` mode, `CORS_ALLOW_ALL_ORIGINS = True` enables smooth development.
- For production, allowed origins can be explicitly specified via the `CORS_ALLOWED_ORIGINS` environment variable (e.g. `http://localhost:5173,https://my-app.com`).
- Vite's dev server also includes a pre-configured reverse proxy to `/api` in [frontend/vite.config.ts](file:///frontend/vite.config.ts).

---

## 📡 API Reference

### Health & Diagnostic Check
- **`GET /api/rag/health/`**
  - Returns ChromaDB status, vector item count, SQLite/PostgreSQL status, and system version.

### Compliance Query Verification
- **`POST /api/rag/query/`**
  - Body:
    ```json
    {
      "query": "What is the maximum inspection interval for pressure relief valves?",
      "standard_codes": ["ASME-VIII"],
      "top_k": 4,
      "strict_mode": true
    }
    ```
  - Response:
    ```json
    {
      "query": "What is the maximum inspection interval for pressure relief valves?",
      "verdict": "COMPLIANT",
      "confidence_score": 0.94,
      "summary": "Verified against standard requirements...",
      "detailed_findings": "Analysis confirmed applicable provisions under ASME-VIII (UG-125)...",
      "citations": [
        {
          "chunk_id": "ASME-VIII_1_chk_1_a9f120",
          "standard_code": "ASME-VIII",
          "clause": "Section VIII UG-125",
          "source": "asme_bpvc_sec_viii_div1.txt",
          "snippet": "UG-125(c) Relief valves shall be inspected and tested periodically...",
          "relevance_score": 0.88
        }
      ],
      "audit_id": 1,
      "latency_ms": 32.5,
      "timestamp": "2026-10-24T23:30:00Z"
    }
    ```

### Document Ingestion
- **`POST /api/rag/ingest/`**
  - Ingests standard text/specifications, executes clause-aware chunking, generates embeddings, and persists to ChromaDB.

### Seed Initial Standards
- **`POST /api/rag/seed/`**
  - Instant one-click seeding of ISO 9001:2015, ASME Section VIII, and IEC 61508 into ChromaDB and Django DB.

### Audit Trail Logs
- **`GET /api/rag/audit-logs/`**
  - Chronological list of past queries, verdicts, confidence ratings, and citations.

---

## ⚡ Statutory Regulation Ingestion (`compliance_core.ingestion`)

The `compliance_core.ingestion` module provides regex-driven, hierarchical parsing of statutory UK electrical regulations and industry guidance, specifically:
- **Statutory Law**: The Electricity at Work Regulations 1989 (EAWR / SI 1989 No. 635) & HSE HSR25 Memorandum of Guidance
- **Engineering Guidance**: Electrical Safety First (ESF) Best Practice Guide 4 (EICR Classification Codes C1, C2, C3, FI)

Unlike generic text splitters that break text naively by character count, this module preserves exact statutory legal structure:
- **`standard`**: Canonical standard/regulation name.
- **`regulation_number`**: e.g., `Regulation 4`, `Regulation 14`, `Regulation 16`.
- **`sub_clause`**: e.g., `Regulation 4(1)`, `Regulation 4(2)`, `Regulation 4(4)`.
- **`duty_holder`**: Statutory classification distinguishing **"Absolute"** duties from duties qualified by **"Reasonably Practicable"** (SFARP).
- **`parent_title`**: e.g., `Systems, work activities and protective equipment`.
- **`raw_text`**: Complete, unsevered statutory clause text.
- **`defense_available`**: Regulation 29 statutory due diligence defense flag.

### CLI Management Command

Ingest regulations from PDF, Markdown, or clean text directly from the command line:

```bash
cd backend

# 1. Ingest EAWR 1989 statutory text (persists into ChromaDB & Django ORM)
python manage.py ingest_regulations --file data/regulations/eawr_1989.txt

# 2. Ingest ESF Best Practice Guide 4
python manage.py ingest_regulations --file data/regulations/esf_bpg4.md

# 3. Dry-run mode with detailed chunk inspection (no database writes)
python manage.py ingest_regulations --file data/regulations/eawr_1989.txt --dry-run --show-chunks

# 4. Ingest and export structured Pydantic chunks to JSON
python manage.py ingest_regulations --file data/regulations/eawr_1989.txt --output-json data/eawr_chunks.json

# 5. Ingest multi-page statutory PDF (using pdfplumber / pypdf)
python manage.py ingest_regulations --file path/to/HSR25.pdf --standard "HSE HSR25 Memorandum of Guidance"
```

---

## 📱 Mobile (Capacitor) & Desktop (Electron) Wrapping

The frontend is structured with:
- `viewport-fit=cover` and CSS `env(safe-area-inset-*)` support for mobile notches/dynamic islands.
- Responsive mobile-first grid.
- [frontend/capacitor.config.ts](file:///frontend/capacitor.config.ts) for instant mobile deployment:

```bash
# Add iOS or Android targets
cd frontend
npm run build
npx cap add android
npx cap add ios
npx cap sync
npx cap open android
```
