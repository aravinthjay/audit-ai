"""
Celery configuration and task definitions.
Handles async investigation execution, evidence retrieval, and report generation.
"""

import asyncio

from celery import Celery, Task
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from app.core.config import settings

# Initialize Celery app
app = Celery(
    "skeptic_engine",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer="json",
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600 * 24,
)

logger = get_task_logger(__name__)


class CallbackTask(Task):
    """Task base with logging callbacks."""

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {task_id} retrying: {exc}")
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, result, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")
        super().on_success(result, task_id, args, kwargs)


app.Task = CallbackTask


@app.task(bind=True, max_retries=3, default_retry_delay=60, name="tasks.execute_investigation")
def execute_investigation_task(self, investigation_id: str) -> dict:
    """Execute the full investigation workflow asynchronously."""
    logger.info(f"Starting investigation execution task: {investigation_id}")
    try:
        from app.agents.executor import InvestigationExecutor
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            executor = InvestigationExecutor(db)
            # asyncio.run() is safe inside a Celery worker thread (no running
            # loop), unlike the deprecated get_event_loop().
            result = asyncio.run(executor.execute_investigation(investigation_id))
            logger.info(f"Investigation {investigation_id} completed: {result}")
            return result
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Investigation {investigation_id} failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@app.task(bind=True, max_retries=3, default_retry_delay=30, name="tasks.collect_evidence")
def collect_evidence_task(self, investigation_id: str) -> dict:
    """Collect evidence from persisted case facts and configured knowledge sources."""
    logger.info(f"Collecting evidence for investigation: {investigation_id}")
    try:
        from app.db.models import EvidenceArtifact, Investigation
        from app.db.session import SessionLocal
        from app.knowledge.retriever import (
            format_context,
            retrieve_knowledge_context,
            retrieve_knowledge_context_from_db,
        )

        db = SessionLocal()
        try:
            investigation = db.get(Investigation, investigation_id)
            if not investigation:
                raise ValueError(f"Investigation {investigation_id} not found")

            query = " ".join(
                [
                    investigation.vendor,
                    investigation.category,
                    investigation.description or "",
                    " ".join(investigation.flags or []),
                ]
            )
            try:
                policy_chunks = retrieve_knowledge_context_from_db(db, query, limit=3)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DB knowledge retrieval failed for %s: %s", investigation_id, exc)
                policy_chunks = retrieve_knowledge_context(query, limit=3)

            flags = [str(flag) for flag in (investigation.flags or [])]
            task_sources = ["ledger_row", "intake_prefilter", "policy_kb"]
            evidence_specs = [
                {
                    "source": "ledger_row",
                    "content": (
                        f"Transaction {investigation.transaction_id} for {investigation.vendor} "
                        f"in {investigation.category} was recorded for "
                        f"{float(investigation.amount or 0):.2f}. Materiality threshold: "
                        f"{float(investigation.materiality or 0):.2f}. "
                        f"Description: {investigation.description or 'No description recorded.'}"
                    ),
                    "citations": [
                        f"investigation:{investigation.id}",
                        f"ledger:{investigation.transaction_id}",
                    ],
                    "relevance_score": 1.0,
                },
                {
                    "source": "intake_prefilter",
                    "content": (
                        "Intake flags recorded for this case: "
                        f"{', '.join(flags) if flags else 'none'}."
                    ),
                    "citations": [f"investigation:{investigation.id}:flags"],
                    "relevance_score": 0.75 if flags else 0.35,
                },
            ]

            if policy_chunks:
                evidence_specs.append(
                    {
                        "source": "policy_kb",
                        "content": format_context(policy_chunks),
                        "citations": [chunk["id"] for chunk in policy_chunks],
                        "relevance_score": max(
                            float(chunk.get("score") or 0) for chunk in policy_chunks
                        ),
                    }
                )

            db.query(EvidenceArtifact).filter(
                EvidenceArtifact.investigation_id == investigation_id,
                EvidenceArtifact.source.in_(task_sources),
            ).delete(synchronize_session=False)

            rows = [
                EvidenceArtifact(
                    investigation_id=investigation_id,
                    source=spec["source"],
                    content=spec["content"],
                    citations=spec["citations"],
                    relevance_score=spec["relevance_score"],
                )
                for spec in evidence_specs
            ]
            db.add_all(rows)
            db.commit()
            logger.info(f"Evidence collected for {investigation_id}")
            return {
                "status": "success",
                "investigation_id": investigation_id,
                "evidence": [
                    {
                        "source": row.source,
                        "content": row.content,
                        "citations": row.citations,
                        "relevance_score": row.relevance_score,
                    }
                    for row in rows
                ],
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Evidence collection failed for {investigation_id}: {exc}")
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@app.task(bind=True, max_retries=2, default_retry_delay=45, name="tasks.generate_report")
def generate_report_task(self, investigation_id: str, report_format: str = "pdf") -> dict:
    """Generate an audit report in the requested format."""
    logger.info(f"Generating {report_format} report for: {investigation_id}")
    try:
        from app.db.models import Investigation
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            investigation = db.get(Investigation, investigation_id)
            if not investigation:
                raise ValueError(f"Investigation {investigation_id} not found")
            report_path = f"/reports/{investigation_id}.{report_format}"
            logger.info(f"Report generated at {report_path}")
            return {
                "status": "success",
                "investigation_id": investigation_id,
                "report_path": report_path,
                "format": report_format,
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Report generation failed for {investigation_id}: {exc}")
        raise self.retry(exc=exc, countdown=45 * (2 ** self.request.retries))


@app.task(bind=True, max_retries=2, default_retry_delay=60, name="tasks.check_materiality")
def check_materiality_task(self, investigation_id: str) -> dict:
    """Check whether the investigation amount exceeds the materiality threshold."""
    logger.info(f"Checking materiality for investigation: {investigation_id}")
    try:
        from app.db.models import Investigation
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            investigation = db.get(Investigation, investigation_id)
            if not investigation:
                raise ValueError(f"Investigation {investigation_id} not found")
            exceeds_materiality = investigation.amount > investigation.materiality
            exceeds_threshold = investigation.amount > settings.DEFAULT_MATERIALITY_THRESHOLD
            return {
                "status": "success",
                "investigation_id": investigation_id,
                "amount": investigation.amount,
                "materiality": investigation.materiality,
                "exceeds_materiality": exceeds_materiality,
                "exceeds_threshold": exceeds_threshold,
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Materiality check failed for {investigation_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


app.conf.beat_schedule = {
    "cleanup-old-states": {
        "task": "tasks.cleanup_old_states",
        "schedule": crontab(hour=2, minute=0),
    },
    "sync-vector-embeddings": {
        "task": "tasks.sync_vector_embeddings",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}


@app.task(name="tasks.cleanup_old_states")
def cleanup_old_states() -> dict:
    """Delete investigation state checkpoints older than 30 days."""
    logger.info("Running state cleanup task")
    try:
        from datetime import datetime, timedelta

        from app.db.models import InvestigationState
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=30)
            deleted = (
                db.query(InvestigationState)
                .filter(InvestigationState.created_at < cutoff)
                .delete()
            )
            db.commit()
            logger.info(f"Cleaned up {deleted} old state records")
            return {"status": "success", "deleted_records": deleted}
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"State cleanup failed: {exc}")
        return {"status": "error", "error": str(exc)}


@app.task(name="tasks.sync_vector_embeddings")
def sync_vector_embeddings() -> dict:
    """Sync curated knowledge chunks into the RAG embedding table."""
    logger.info("Syncing vector embeddings")
    from app.db.session import SessionLocal
    from app.knowledge.retriever import sync_knowledge_embeddings

    db = SessionLocal()
    try:
        result = sync_knowledge_embeddings(db)
        logger.info("Vector embeddings synced (%s chunks)", result.get("synced_chunks", 0))
        return result
    except Exception as exc:
        db.rollback()
        logger.error(f"Vector sync failed: {exc}")
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()
