# ExamGuard AI — Intelligent Examination and Integrity Assessment System

[![Stage 1](https://img.shields.io/badge/Stage-1:_Project_Foundation-blue.svg)](#current-implementation-status)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js_15_%7C_TypeScript_%7C_Tailwind_CSS-000000.svg)](./frontend)
[![Backend](https://img.shields.io/badge/Backend-FastAPI_%7C_Python_3.11+_%7C_SQLAlchemy_2.0-009688.svg)](./backend)
[![Database](https://img.shields.io/badge/Database-PostgreSQL_16_%7C_Alembic-336791.svg)](./backend/alembic)

---

## 1. What is ExamGuard AI?

**ExamGuard AI** is an enterprise-grade, AI-powered online examination and proctoring platform designed to deliver secure, adaptive, and scalable assessment experiences for modern educational institutions and certifications.

### Core Vision & System Features
- **Multi-Role Access**: Role-based access control for **Students**, **Examiners**, and **Administrators**.
- **Question Bank Management**: Categorized, tagged, and randomized paper creation.
- **Server-Controlled Sessions**: Cryptographically synchronized timers and state-bound exam sessions.
- **Diverse Question Types**: MCQs, multi-select, short-answer, long-answer, and handwritten image submission support.
- **AI-Assisted Evaluation**: LLM-driven subjective answer scoring with confidence scoring.
- **Automated Proctoring**: Real-time multi-modal proctoring (head pose, object detection, gaze tracking, tab switches).
- **Integrity Analytics**: Cross-student answer similarity detection and anomaly analysis.
- **Examiner Overrides**: Transparent review system allowing manual score overrides and audit trailing.
- **Responsive PWA**: Seamless cross-device experience across desktop, tablet, and mobile browsers.

---

## 2. Technology Stack

### Frontend
- **Framework**: Next.js 15 (App Router) & React 19
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS & Lucide Icons
- **PWA Capabilities**: Service workers & web-app manifest support (future stages)

### Backend
- **Framework**: FastAPI & Uvicorn
- **Language**: Python 3.11+
- **Data Validation**: Pydantic v2
- **ORM & Migrations**: SQLAlchemy 2.0 & Alembic
- **Database**: PostgreSQL 16
- **Testing**: Pytest & FastAPI TestClient

### Infrastructure & DevOps
- **Containerization**: Docker & Docker Compose
- **Environment Management**: `.env` configuration pattern

---

## 3. Monorepo Project Structure

```text
EXAMGUARD_AI/
│
├── frontend/                     # Next.js Frontend Application
│   ├── app/                      # Next.js App Router (pages, layout, styles)
│   │   ├── layout.tsx            # Global layout shell
│   │   ├── page.tsx              # Landing page component
│   │   └── globals.css           # Global Tailwind CSS styles
│   ├── components/               # Reusable UI components
│   ├── lib/                      # Helper functions & utilities
│   ├── hooks/                    # Custom React hooks
│   ├── types/                    # TypeScript interfaces & type declarations
│   ├── public/                   # Static assets & public resources
│   ├── package.json              # Frontend npm dependencies & scripts
│   ├── tsconfig.json             # TypeScript compiler configuration
│   ├── next.config.ts            # Next.js framework configuration
│   ├── tailwind.config.ts        # Tailwind theme styling config
│   ├── postcss.config.mjs        # PostCSS configuration
│   ├── Dockerfile                # Frontend container spec
│   └── .env.example              # Frontend environment template
│
├── backend/                      # FastAPI Backend Application
│   ├── app/                      # Core application package
│   │   ├── api/                  # REST API routes & controllers
│   │   │   └── health.py         # Healthcheck endpoint
│   │   ├── core/                 # App settings, security & middleware
│   │   │   └── config.py         # Pydantic settings manager
│   │   ├── db/                   # Database engine, session, & declarative base
│   │   │   ├── base.py           # DeclarativeBase class
│   │   │   └── session.py        # SQLAlchemy SessionLocal generator
│   │   ├── models/               # SQLAlchemy ORM database models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Core business logic layer
│   │   ├── repositories/         # Data access & database queries
│   │   └── main.py               # FastAPI application entry point
│   ├── alembic/                  # Database migration scripts
│   │   ├── env.py                # Migration environment runner
│   │   └── script.py.mako        # Migration template
│   ├── tests/                    # Backend automated unit & API tests
│   ├── alembic.ini               # Alembic configuration file
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile                # Backend container spec
│
├── docs/                         # Technical documentation & design specs
│   └── architecture.md           # System architecture overview
│
├── .env.example                  # Root environment configuration template
├── .gitignore                    # Version control exclusion rules
├── README.md                     # Project documentation
└── docker-compose.yml            # Multi-container orchestration spec
```

---

## 4. Environment Variables

Copy `.env.example` to `.env` before running locally:

```bash
cp .env.example .env
```

Key environment configurations:

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://examguard_user:examguard_password@localhost:5432/examguard_db` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | `dev_jwt_secret_key_change_in_production` |
| `FRONTEND_URL` | Allowed CORS frontend URL | `http://localhost:3000` |
| `BACKEND_URL` | Backend service base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_API_URL` | API target for frontend client | `http://localhost:8000` |
| `GEMINI_API_KEY` | Gemini LLM service key | `your_gemini_api_key_here` |

---

## 5. How to Run Frontend Locally

1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run dev server:
   ```bash
   npm run dev
   ```
4. Access landing page at `http://localhost:3000`.

---

## 6. How to Run Backend Locally

1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
5. Verify health check:
   - Root: `http://localhost:8000/`
   - Healthcheck: `http://localhost:8000/api/health`
   - OpenAPI Docs: `http://localhost:8000/docs`

---

## 7. How PostgreSQL is Configured

PostgreSQL is configured using **SQLAlchemy 2.0** ORM engine and session management in `backend/app/db/session.py`. Database migrations are handled via **Alembic**.

### Running Migrations via Alembic
```bash
cd backend
# Generate migration script (in future stages)
alembic revision --autogenerate -m "create initial schema"

# Apply migrations
alembic upgrade head
```

---

## 8. Docker Compose Local Setup

To run all services (PostgreSQL, Backend API, Frontend Web) simultaneously:

```bash
docker-compose up --build
```

Services exposed:
- **Frontend App**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **PostgreSQL**: `localhost:5432`

---

## 9. Current Implementation Status

> [!IMPORTANT]
> **Stage 1 — Project Foundation**: COMPLETE.
>
> - Monorepo architecture initialized.
> - Next.js landing page shell configured with API health check integration.
> - FastAPI application initialized with `/` and `/api/health` endpoints.
> - SQLAlchemy database engine and Alembic migration structure initialized.
> - Docker Compose multi-container setup configured.
>
> **Note**: Database schema design and entity models will be implemented separately in **Stage 2**.
