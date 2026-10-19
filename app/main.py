from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.models import SearchRequest
from app.registry import SourceRegistry
from app.search import SearchService
from app.settings import Settings
from app.xlsx import build_workbook
from app.jobs import JobManager

settings = Settings.from_env()
registry = SourceRegistry(settings.sources_file)
jobs = JobManager()
search_service = SearchService(registry, jobs, settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await jobs.shutdown()


app = FastAPI(
    title="Media Monitoring API",
    version="0.1.0",
    description="Поиск публикаций в публичных источниках Красноярского края.",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sources")
async def list_sources() -> dict[str, object]:
    return {"sources": registry.list_sources()}


@app.post("/jobs", status_code=202)
async def create_job(request: SearchRequest) -> dict[str, object]:
    selected = registry.resolve_selection(request.platform, request.editor)
    if not selected:
        raise HTTPException(
            status_code=422,
            detail="Для выбранных редакций и площадок не найдено URL в реестре источников.",
        )
    return await search_service.start(request, selected)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, object]:
    job = await jobs.snapshot(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задание не найдено.")
    return job


@app.get("/jobs/{job_id}/export.xlsx")
async def export_job(job_id: str) -> StreamingResponse:
    job = await jobs.snapshot(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задание не найдено.")
    content = build_workbook(job)
    return StreamingResponse(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="media-search-{job_id}.xlsx"'},
    )
