from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai_routes, auth, investigations, share, upload
from app.core.config import CORS_ORIGINS
from app.core.limiter import RateLimiter

app = FastAPI(
    title="Hamrabi — OSINT Intelligence Platform",
    description="AI-assisted OSINT investigation & correlation platform "
                "(legal/academic use only, public sources).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiter, max_requests=60, per_seconds=60)

app.include_router(auth.router)
app.include_router(investigations.router)
app.include_router(upload.router)
app.include_router(ai_routes.router)
app.include_router(share.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "hamrabi-backend"}


@app.get("/", include_in_schema=False)
def root():
    return {
        "system": "Hamrabi OSINT Platform",
        "message": "Backend is running. Use the web UI on http://localhost:5173, "
                   "API docs on /docs, or call the /api endpoints.",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)