from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.questions import router as questions_router
from app.api.dashboard import router as dashboard_router
from app.api.ai_questions import router as ai_questions_router
from app.api.question_import import router as question_import_router
from app.api.exams import router as exams_router
from app.api.student_exams import router as student_exams_router
from app.api.proctoring import router as proctoring_router
from app.api.results import router as results_router
from app.api.analytics import router as analytics_router
from app.api.integrity import router as integrity_router
from app.api.identity import router as identity_router
from app.api.cross_student import router as cross_student_router
from app.api.admin import router as admin_router
from app.api.academic import router as academic_router
from app.api.examiner import router as examiner_router
from app.api.users import router as users_router

import os
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="ExamGuard AI — Intelligent Examination and Integrity Assessment System API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Ensure uploads directory exists and mount static route
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Set up CORS middleware for credentialed requests
origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(dashboard_router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"])
app.include_router(examiner_router, prefix=settings.API_V1_STR, tags=["Examiner Dashboard"])
app.include_router(ai_questions_router, prefix=f"{settings.API_V1_STR}/questions", tags=["AI Question Generator"])
app.include_router(question_import_router, prefix=f"{settings.API_V1_STR}/questions/import", tags=["Question Import"])
app.include_router(questions_router, prefix=f"{settings.API_V1_STR}/questions", tags=["Question Bank"])
app.include_router(exams_router, prefix=f"{settings.API_V1_STR}/exams", tags=["Exam Management"])
app.include_router(student_exams_router, prefix=settings.API_V1_STR, tags=["Student Exams"])
app.include_router(proctoring_router, prefix=settings.API_V1_STR, tags=["Proctoring"])
app.include_router(results_router, prefix=settings.API_V1_STR, tags=["Results"])
app.include_router(analytics_router, prefix=settings.API_V1_STR, tags=["Analytics"])
app.include_router(integrity_router, prefix=settings.API_V1_STR, tags=["Integrity Intelligence"])
app.include_router(identity_router, prefix=settings.API_V1_STR, tags=["Student Identity Verification"])
app.include_router(cross_student_router, prefix=settings.API_V1_STR, tags=["Cross-Student Integrity Analysis"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["User Profile & Settings"])
app.include_router(admin_router, prefix=settings.API_V1_STR, tags=["Admin User Management"])
app.include_router(academic_router, prefix=settings.API_V1_STR, tags=["Academic & Institution Management"])


@app.get("/")
def read_root():
    """Root endpoint returning API status information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "online",
        "docs_url": "/docs"
    }


def custom_openapi():
    """Configures HTTP Bearer authentication in OpenAPI Swagger UI."""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Apply security globally to protected endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if path in [f"{settings.API_V1_STR}/auth/me"] or path.startswith(f"{settings.API_V1_STR}/questions") or path.startswith(f"{settings.API_V1_STR}/dashboard") or path.startswith(f"{settings.API_V1_STR}/examiner"):
                openapi_schema["paths"][path][method]["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
