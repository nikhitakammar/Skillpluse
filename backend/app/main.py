from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import analytics, assessments, auth, batches, predictions, recommendations, students

app = FastAPI(
    title="Skill Pluse API",
    description="Training performance and skill gap intelligence API.",
    version="0.1.0",
)

app.include_router(batches.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(assessments.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get(
        "SKILLPULSE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Confirm the API process is ready to respond."""
    return {"status": "ok", "service": "Skill Pluse API"}
