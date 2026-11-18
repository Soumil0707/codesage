"""Worker Process Runner: Continuously executes MySQL-backed background tasks."""
import os
import sys
import time
import signal
import socket
import asyncio
import logging
from typing import Dict, Any

from app.config import get_settings
from app.database import SyncSessionLocal, AsyncSessionLocal
from app.models.jobs import JobType
from app.workers.task_queue import TaskQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
)
logger = logging.getLogger("codesage.worker")
settings = get_settings()

worker_id = f"worker-{socket.gethostname()}-{os.getpid()}"
running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("Shutdown signal received. Finishing active tasks...")
    running = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


async def process_job_async(job_id: str, job_type: JobType, repo_id: str, version_id: str, payload: Dict[str, Any]):
    """Execute asynchronous domain services based on job type."""
    from app.services.rag_service import RAGService
    from app.services.review_service import ReviewService
    from app.models.analysis import ReportType

    async with AsyncSessionLocal() as async_db:
        if job_type in (JobType.FILE_PARSING, JobType.EMBEDDING_GENERATION, JobType.REPO_INGESTION):
            logger.info("Executing indexing & RAG embedding pipeline for version %s", version_id)
            result = await RAGService.index_version(version_id, async_db)
            return result
        elif job_type == JobType.CODE_ANALYSIS:
            logger.info("Executing automated code review for version %s", version_id)
            report = await ReviewService.run_review(
                repository_id=repo_id,
                version_id=version_id,
                report_type=ReportType.FULL_ANALYSIS,
                file_paths=payload.get("file_paths"),
                db=async_db,
            )
            return {"report_id": report.id, "total_issues": report.total_issues}
        else:
            logger.info("Unrecognized or no-op job type: %s", job_type)
            return {"status": "skipped"}


def run_worker_loop():
    logger.info("Starting CodeSage background worker: %s", worker_id)
    from app.database import sync_engine, Base
    import app.models  # noqa: F401
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Verified/created database tables for worker.")
    except Exception as e:
        logger.warning("Worker database initialization check: %s", str(e))

    while running:
        with SyncSessionLocal() as sync_db:
            try:
                # 1. Recover stale tasks if any
                TaskQueue.recover_stale_jobs(sync_db, timeout_seconds=settings.JOB_TIMEOUT)

                # 2. Claim next available job
                job = TaskQueue.dequeue(worker_id, sync_db)

                if job:
                    logger.info("Claimed job %s (type: %s, repo: %s)", job.id, job.job_type, job.repository_id)
                    import json
                    payload = json.loads(job.payload_json) if job.payload_json else {}

                    try:
                        # Process job asynchronously
                        result = asyncio.run(
                            process_job_async(
                                job_id=job.id,
                                job_type=job.job_type,
                                repo_id=job.repository_id,
                                version_id=job.version_id,
                                payload=payload,
                            )
                        )
                        TaskQueue.complete(job.id, result, sync_db)
                        logger.info("Successfully completed job %s", job.id)
                    except Exception as exc:
                        logger.error("Job %s execution failed: %s", job.id, str(exc), exc_info=True)
                        TaskQueue.fail(job.id, str(exc), sync_db)
                else:
                    # Sleep before next poll
                    time.sleep(settings.WORKER_POLL_INTERVAL)

            except Exception as e:
                logger.error("Error in worker polling loop: %s", str(e), exc_info=True)
                time.sleep(settings.WORKER_POLL_INTERVAL)

    logger.info("Worker %s shut down gracefully.", worker_id)


if __name__ == "__main__":
    run_worker_loop()
