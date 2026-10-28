"""Backfill vector embeddings for published knowledge chunks."""
import logging
import sys
from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.modules.knowledge.chunking import split_content
from app.modules.knowledge.embeddings import generate_embeddings
from app.modules.platform.models import KnowledgeChunk, KnowledgeDocument, KnowledgeStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_embeddings")


def main() -> None:
    with SessionLocal() as database:
        # Step 1: Check published documents without chunks
        published_docs = list(database.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.status == KnowledgeStatus.PUBLISHED)
        ))
        logger.info("Encontrados %d documentos publicados.", len(published_docs))

        chunks_created = 0
        for doc in published_docs:
            existing_count = database.scalar(
                select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.document_id == doc.id)
            )
            if existing_count == 0:
                logger.info("Documento '%s' (%s) sem chunks. Gerando chunks e embeddings...", doc.title, doc.id)
                contents = split_content(doc.content)
                if contents:
                    vectors = generate_embeddings(contents)
                    for pos, (content, vec) in enumerate(zip(contents, vectors)):
                        database.add(KnowledgeChunk(
                            tenant_id=doc.tenant_id,
                            environment_id=doc.environment_id,
                            assistant_id=doc.assistant_id,
                            document_id=doc.id,
                            position=pos,
                            content=content,
                            embedding=vec,
                        ))
                        chunks_created += 1
        if chunks_created > 0:
            database.commit()
            logger.info("Criados %d chunks com embeddings a partir de documentos sem chunks.", chunks_created)

        # Step 2: Update existing chunks where embedding is NULL
        chunks_missing_embedding = list(database.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.embedding.is_(None))
        ))
        total_missing = len(chunks_missing_embedding)
        logger.info("Encontrados %d chunks sem embedding vetorial.", total_missing)

        if total_missing == 0:
            logger.info("Todos os chunks já possuem embeddings. Concluído com sucesso.")
            return

        batch_size = 32
        for i in range(0, total_missing, batch_size):
            batch = chunks_missing_embedding[i:i + batch_size]
            texts = [chunk.content for chunk in batch]
            vectors = generate_embeddings(texts)
            for chunk, vec in zip(batch, vectors):
                chunk.embedding = vec
            database.commit()
            logger.info("Processados %d / %d chunks...", min(i + batch_size, total_missing), total_missing)

        logger.info("Backfill de embeddings finalizado com sucesso!")


if __name__ == "__main__":
    main()
