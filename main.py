"""
HealthSaaS — Multi-Tenant Healthcare Chatbot Platform
FastAPI Backend Entrypoint
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from db.mongodb import connect_db, close_db, get_db, create_indexes
from api.routes import auth, chat, clinic, admin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await connect_db()
    db = get_db()
    await create_indexes(db)
    print("🚀 HealthSaaS API is ready!")
    yield
    # Shutdown
    await close_db()
    print("👋 HealthSaaS API shutdown complete")


app = FastAPI(
    title="HealthSaaS API",
    description="Multi-Tenant Healthcare Chatbot Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── ROUTES ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(clinic.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "service": "HealthSaaS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


# ─── DEV RUNNER ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info",
    )
