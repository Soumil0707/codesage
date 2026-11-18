"""MySQL-backed Task Queue: Idempotency, atomic job claiming, retries, and worker recovery."""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_

from app.models.jobs import IndexingJob, JobStatus, JobType

logger = logging.getLogger("codesage.task_queue")


class TaskQueue:
    @classmethod
    def enqueue(
        cls,
        repository_id: str,
        job_type: JobType,
        db: Session,
        version_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        idempotency_key: Optional[str] = None,
    ) -> IndexingJob:
        """Enqueue a background task with optional idempotency key."""
        if idempotency_key:
            stmt = select(IndexingJob).where(
                IndexingJob.idempotency_key == idempotency_key,
                IndexingJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING, JobStatus.COMPLETED]),
            )
            existing = db.execute(stmt).scalars().first()
            if existing:
                logger.info("Job already enqueued with idempotency key: %s", idempotency_key)
                return existing

        job = IndexingJob(
            repository_id=repository_id,
            version_id=version_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            priority=priority,
            payload_json=json.dumps(payload) if payload else None,
            idempotency_key=idempotency_key,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def dequeue(cls, worker_id: str, db: Session) -> Optional[IndexingJob]:
        """Atomically claim the highest priority PENDING or RETRYING job."""
        now = datetime.utcnow()

        # Check for pending or ready retrying job
        stmt = (
            select(IndexingJob)
            .where(
                IndexingJob.status.in_([JobStatus.PENDING, JobStatus.RETRYING]),
                IndexingJob.scheduled_at <= now,
            )
            .order_by(IndexingJob.priority.desc(), IndexingJob.scheduled_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = db.execute(stmt).scalars().first()

        if job:
            job.status = JobStatus.RUNNING
            job.worker_id = worker_id
            job.started_at = now
            db.commit()
            db.refresh(job)
            return job

        return None

    @classmethod
    def complete(cls, job_id: str, result: Optional[Dict[str, Any]], db: Session):
        """Mark job as completed with results."""
        stmt = select(IndexingJob).where(IndexingJob.id == job_id)
        job = db.execute(stmt).scalars().first()
        if job:
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.completed_at = datetime.utcnow()
            if result:
                job.result_json = json.dumps(result)
            db.commit()

    @classmethod
    def fail(cls, job_id: str, error_message: str, db: Session):
        """Record job failure with retry backoff."""
        stmt = select(IndexingJob).where(IndexingJob.id == job_id)
        job = db.execute(stmt).scalars().first()
        if not job:
            return

        job.retry_count += 1
        job.error_message = error_message

        if job.retry_count < job.max_retries:
            job.status = JobStatus.RETRYING
            # Exponential backoff: 5s, 20s, 45s
            backoff_secs = 5 * (job.retry_count ** 2)
            job.scheduled_at = datetime.utcnow() + timedelta(seconds=backoff_secs)
            logger.warning("Job %s failed (attempt %d/%d). Retrying in %ds: %s", job_id, job.retry_count, job.max_retries, backoff_secs, error_message)
        else:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            logger.error("Job %s permanently failed after %d attempts: %s", job_id, job.max_retries, error_message)

        db.commit()

    @classmethod
    def recover_stale_jobs(cls, db: Session, timeout_seconds: int = 600) -> int:
        """Find RUNNING jobs exceeding timeout and set them to retry or fail."""
        cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        stmt = select(IndexingJob).where(
            IndexingJob.status == JobStatus.RUNNING,
            IndexingJob.started_at < cutoff,
        )
        stale_jobs = db.execute(stmt).scalars().all()

        recovered_count = 0
        for job in stale_jobs:
            logger.warning("Recovering stale job %s (worker: %s, started_at: %s)", job.id, job.worker_id, job.started_at)
            job.status = JobStatus.TIMEOUT
            cls.fail(job.id, f"Worker timed out after {timeout_seconds}s", db)
            recovered_count += 1

        return recovered_count
