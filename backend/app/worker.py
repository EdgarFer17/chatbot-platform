import logging
import time

from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.modules.knowledge.sync_service import run_knowledge_sync
from app.modules.platform.models import KnowledgeSyncJob, SyncJobStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("chatbot-platform-worker")


def recover_interrupted_jobs() -> None:
    with SessionLocal() as database:
        database.execute(
            update(KnowledgeSyncJob)
            .where(KnowledgeSyncJob.status == SyncJobStatus.RUNNING)
            .values(status=SyncJobStatus.PENDING, error_message="Execução retomada após reinicialização do worker")
        )
        database.commit()


def claim_next_job():
    with SessionLocal() as database:
        job = database.scalar(
            select(KnowledgeSyncJob)
            .where(KnowledgeSyncJob.status == SyncJobStatus.PENDING)
            .order_by(KnowledgeSyncJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = SyncJobStatus.RUNNING
        database.commit()
        return job.id


def main() -> None:
    logger.info("Worker de conhecimento iniciado")
    recover_interrupted_jobs()
    while True:
        job_id = claim_next_job()
        if job_id is None:
            time.sleep(1.5)
            continue
        logger.info("Processando sincronização %s", job_id)
        run_knowledge_sync(job_id)


if __name__ == "__main__":
    main()
