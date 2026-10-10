# ExamGuard AI — Architecture Overview

## Project Name
**ExamGuard AI — Intelligent Examination and Integrity Assessment System**

## High-Level Architecture Overview

```text
                                  +---------------------------------------+
                                  |         Next.js Frontend (PWA)       |
                                  | TypeScript, React 19, Tailwind CSS    |
                                  +-------------------+-------------------+
                                                      |
                                        HTTP / REST   |   WebSockets (Future)
                                                      v
                                  +-------------------+-------------------+
                                  |          FastAPI Backend              |
                                  |  Python, Pydantic, SQLAlchemy 2.0     |
                                  +---------+-------------------+---------+
                                            |                   |
                                            v                   v
                                  +---------+-------+   +-------+---------+
                                  |   PostgreSQL    |   |    AI Engine    |
                                  |   Database      |   |  (Gemini/LLM)   |
                                  +-----------------+   +-----------------+
```

## Modular Layering

### Frontend (`/frontend`)
- **App Router**: Modern route structure with server & client components.
- **State & Hooks**: Dedicated hooks directory for proctoring feeds, exam timers, and real-time state.
- **Design System**: Tailored dark/neutral visual design with responsive layouts and micro-interactions.

### Backend (`/backend`)
- **Core (`app/core/`)**: Configuration settings, security utilities, global middleware.
- **API (`app/api/`)**: REST endpoints cleanly separated into modular routers.
- **DB (`app/db/`)**: Database session management, declarative models base, and migrations (Alembic).
- **Models (`app/models/`)**: SQLAlchemy ORM entity definitions.
- **Schemas (`app/schemas/`)**: Pydantic validation request/response schemas.
- **Services (`app/services/`)**: Business logic layer (proctoring analytics, grading engine, assessment rules).
- **Repositories (`app/repositories/`)**: Encapsulated data access layer for clean separation of concerns.

## Stage 1 Status
Currently implemented: **Stage 1 — Project Foundation**.
- Monorepo directory structure created.
- Next.js application shell initialized.
- FastAPI backend framework configured with healthcheck endpoint (`/api/health`).
- SQLAlchemy DB session & engine setup prepared.
- Alembic database migration environment initialized.
- Environment variable configuration (`.env.example`) defined.
- Docker Compose setup for local containerized development.
