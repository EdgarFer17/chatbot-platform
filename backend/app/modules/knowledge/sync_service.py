import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.knowledge.ingestion import (
    MAX_WEBSITE_PAGES,
    IngestionError,
    discover_document_urls,
    discover_sitemap_urls,
    extract_document,
    fetch_public_document,
)
from app.modules.platform.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSyncJob,
    SourceType,
    SyncJobStatus,
    SyncStatus,
)


def run_knowledge_sync(job_id: uuid.UUID) -> None:
    database = SessionLocal()
    try:
        job = database.get(KnowledgeSyncJob, job_id)
        if job is None:
            return
        source = database.get(KnowledgeSource, job.source_id)
        if source is None or not source.source_url or not source.allowed_host:
            raise IngestionError("Fonte inválida ou removida")

        job.status = SyncJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        source.sync_status = SyncStatus.SYNCING
        source.last_error = None
        database.commit()

        root_data, root_mime, final_url = fetch_public_document(source.source_url, source.allowed_host)
        queue: list[tuple[str, str | None, bytes | None, str | None]] = [(final_url, source.name, root_data, root_mime)]
        queued = {final_url.rstrip("/")}
        used_sitemap = False
        source_path = urlparse(source.source_url).path.rstrip("/")
        sitemap_allowed = source.allowed_host.startswith(("docs.", "help.", "documentation.")) or source_path in {"", "/"}
        if source.source_type == SourceType.WEBSITE and sitemap_allowed:
            parsed_root = urlparse(final_url)
            sitemap_url = f"{parsed_root.scheme}://{parsed_root.netloc}/sitemap.xml"
            try:
                sitemap_data, sitemap_mime, resolved_sitemap = fetch_public_document(sitemap_url, source.allowed_host)
                if "xml" in sitemap_mime or resolved_sitemap.endswith(".xml"):
                    sitemap_locations = discover_sitemap_urls(sitemap_data, source.allowed_host)
                    expanded_locations: list[str] = []
                    for location in sitemap_locations:
                        if location.endswith(".xml"):
                            nested_data, _, _ = fetch_public_document(location, source.allowed_host)
                            expanded_locations.extend(discover_sitemap_urls(nested_data, source.allowed_host))
                        else:
                            expanded_locations.append(location)
                    for location in expanded_locations[:MAX_WEBSITE_PAGES]:
                        normalized = location.rstrip("/")
                        if normalized not in queued:
                            queued.add(normalized)
                            queue.append((location, None, None, None))
                    used_sitemap = len(queue) > 1
            except (IngestionError, httpx.HTTPError):
                used_sitemap = False
        job.discovered = min(len(queue), MAX_WEBSITE_PAGES)
        database.commit()

        while queue and job.processed < MAX_WEBSITE_PAGES:
            url, title, prefetched_data, prefetched_mime = queue.pop(0)
            try:
                if prefetched_data is None or prefetched_mime is None:
                    data, mime, resolved = fetch_public_document(url, source.allowed_host)
                else:
                    data, mime, resolved = prefetched_data, prefetched_mime, url

                if source.source_type == SourceType.WEBSITE and not used_sitemap and mime in {"text/html", "application/xhtml+xml"}:
                    for child_url, child_title in discover_document_urls(data, resolved, source.allowed_host):
                        normalized = child_url.rstrip("/")
                        if normalized not in queued and len(queued) < MAX_WEBSITE_PAGES:
                            queued.add(normalized)
                            queue.append((child_url, child_title, None, None))
                    job.discovered = min(len(queued), MAX_WEBSITE_PAGES)

                extracted = extract_document(data, mime, resolved, title)
                current = database.scalar(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.source_id == source.id,
                        KnowledgeDocument.original_url == extracted.url,
                        KnowledgeDocument.is_current.is_(True),
                    )
                )
                if current and current.checksum == extracted.checksum:
                    job.unchanged += 1
                else:
                    version = 1
                    if current:
                        current.is_current = False
                        version = current.version_number + 1
                    database.add(
                        KnowledgeDocument(
                            tenant_id=source.tenant_id,
                            environment_id=source.environment_id,
                            assistant_id=source.assistant_id,
                            source_id=source.id,
                            title=extracted.title,
                            content=extracted.content,
                            original_url=extracted.url,
                            mime_type=extracted.mime_type,
                            checksum=extracted.checksum,
                            version_number=version,
                        )
                    )
                    job.created += 1
            except (IngestionError, httpx.HTTPError) as error:
                job.failed += 1
                job.error_message = f"{job.failed} falha(s). Última falha: {str(error)[:500]}"
            finally:
                job.processed += 1
                database.commit()

        job.status = SyncJobStatus.COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        source.sync_status = SyncStatus.FAILED if job.failed else SyncStatus.READY
        source.last_error = job.error_message if job.failed else None
        source.last_synced_at = job.finished_at
        database.commit()
    except Exception as error:
        database.rollback()
        job = database.get(KnowledgeSyncJob, job_id)
        if job is not None:
            job.status = SyncJobStatus.FAILED
            job.error_message = str(error)[:1000]
            job.finished_at = datetime.now(timezone.utc)
            source = database.get(KnowledgeSource, job.source_id)
            if source is not None:
                source.sync_status = SyncStatus.FAILED
                source.last_error = job.error_message
            database.commit()
    finally:
        database.close()
