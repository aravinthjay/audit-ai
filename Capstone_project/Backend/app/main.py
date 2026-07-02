"""
FastAPI application factory.
Wires middleware, lifespan, and routers for the Skeptic Engine backend.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import (
    agents,
    analytics,
    audit,
    auth,
    claims,
    evaluation,
    health,
    intake,
    investigations,
    knowledge,
    reports,
    reviews,
    websocket,
)
from app.api.routes import (
    settings as settings_routes,
)
from app.core.config import settings
from app.core.request_logging import add_request_logging_middleware
from app.core.security import seed_default_user
from app.db.session import engine, init_db

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Skeptic Engine Backend (env=%s)", settings.ENV)
    init_db()
    logger.info("Database initialized")
    seed_default_user()
    try:
        from app.db.session import SessionLocal
        from app.knowledge.retriever import sync_knowledge_embeddings

        db = SessionLocal()
        try:
            result = sync_knowledge_embeddings(db)
            logger.info("Knowledge base indexed (%s chunks)", result.get("synced_chunks", 0))
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Knowledge base indexing skipped: %s", exc)
    try:
        from app.audit.eventstore import get_audit_log

        await get_audit_log()
        logger.info("EventStoreDB initialized")
    except Exception as e:  # noqa: BLE001
        logger.warning("EventStoreDB unavailable, using Postgres audit fallback: %s", e)
    yield
    logger.info("Shutting down Skeptic Engine Backend")
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Real-time multi-agent AI audit investigation platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    add_request_logging_middleware(app)

    # Health at root; everything else under the API root path.
    app.include_router(health.router)
    app.include_router(auth.router, prefix=settings.API_ROOT_PATH)
    app.include_router(claims.router, prefix=settings.API_ROOT_PATH)
    app.include_router(investigations.router, prefix=settings.API_ROOT_PATH)
    app.include_router(reviews.router, prefix=settings.API_ROOT_PATH)
    app.include_router(evaluation.router, prefix=settings.API_ROOT_PATH)
    app.include_router(agents.router, prefix=settings.API_ROOT_PATH)
    app.include_router(analytics.router, prefix=settings.API_ROOT_PATH)
    app.include_router(reports.router, prefix=settings.API_ROOT_PATH)
    app.include_router(knowledge.router, prefix=settings.API_ROOT_PATH)
    app.include_router(audit.router, prefix=settings.API_ROOT_PATH)
    app.include_router(intake.router, prefix=settings.API_ROOT_PATH)
    app.include_router(settings_routes.router, prefix=settings.API_ROOT_PATH)
    app.include_router(websocket.router, prefix=settings.API_ROOT_PATH)

    @app.get(f"{settings.API_ROOT_PATH}/")
    async def root():
        return {
            "message": "Skeptic Engine Backend API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )
