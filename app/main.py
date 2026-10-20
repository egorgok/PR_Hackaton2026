from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import mimetypes
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.models import FullSearchRequest, SearchRequest
from app.registry import SourceRegistry
from app.search import SearchService
from app.settings import Settings
from app.xlsx import build_workbook
from app.jobs import JobManager

settings = Settings.from_env()
registry = SourceRegistry(settings.sources_file)
jobs = JobManager(settings.jobs_db_file)
search_service = SearchService(registry, jobs, settings)
SESSION_COOKIE = "media_session"


def get_or_create_session(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        return session_id
    session_id = secrets.token_urlsafe(32)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=settings.cookie_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return session_id


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sources")
async def list_sources() -> dict[str, object]:
    return {"sources": registry.list_sources()}


@app.post("/jobs", status_code=202)
async def create_job(
    payload: SearchRequest,
    request: Request,
    response: Response,
) -> dict[str, object]:
    selected = registry.resolve_pairs(payload.resolve_sources())
    session_id = get_or_create_session(request, response)
    return await search_service.start(payload, selected, session_id)


@app.post("/jobs/all", status_code=202)
async def create_full_job(
    payload: FullSearchRequest,
    request: Request,
    response: Response,
) -> dict[str, object]:
    selected = registry.all_sources(payload.platform)
    if not selected:
        raise HTTPException(
            status_code=422,
            detail="В реестре нет источников на выбранных площадках.",
        )
    session_id = get_or_create_session(request, response)
    search_payload = SearchRequest(
        text=payload.text,
        platform=payload.platform,
        editor=list(dict.fromkeys(source.editor for source in selected)),
        days=payload.days,
    )
    result = await search_service.start(search_payload, selected, session_id)
    result["scope"] = "all_registry_sources"
    result["selected_sources"] = len(selected)
    return result


@app.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict[str, object]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        raise HTTPException(status_code=404, detail="Задание не найдено.")
    job = await jobs.snapshot(job_id, session_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задание не найдено.")
    return job


@app.get("/jobs/{job_id}/export.xlsx")
async def export_job(job_id: str, request: Request) -> Response:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        raise HTTPException(status_code=404, detail="Задание не найдено.")
    job = await jobs.snapshot(job_id, session_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задание не найдено.")
    days = request.query_params.get("days")
    include_undated = request.query_params.get("include_undated") == "true"
    platforms = set(request.query_params.getlist("platform"))
    editors = {value.casefold() for value in request.query_params.getlist("editor")}
    filtered = job
    if days or platforms or editors:
        filtered = dict(job)
        results = list(job["results"])
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
            results = [
                item for item in results
                if (
                    (not item.get("published_at") and include_undated)
                    or (
                        item.get("published_at")
                        and datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")) >= cutoff
                    )
                )
            ]
        if platforms:
            results = [item for item in results if item["platform"] in platforms]
        if editors:
            results = [item for item in results if item["editor"].casefold() in editors]
        filtered["results"] = results
        filtered["count"] = len(results)
    content = build_workbook(filtered).getvalue()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="media-search-{job_id}.xlsx"'},
    )


@app.get("/history")
async def get_history(request: Request, response: Response) -> dict[str, object]:
    session_id = get_or_create_session(request, response)
    return {"jobs": await jobs.history(session_id)}


FRONTEND_DIST = Path(__file__).resolve().parents[1] / "Frontend" / "dist"


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    if not FRONTEND_DIST.is_dir():
        raise HTTPException(status_code=404, detail="Frontend не собран.")
    requested = (FRONTEND_DIST / path).resolve()
    if FRONTEND_DIST not in requested.parents and requested != FRONTEND_DIST:
        raise HTTPException(status_code=404, detail="Файл не найден.")
    if requested.is_file():
        media_type, _ = mimetypes.guess_type(requested.name)
        return Response(content=requested.read_bytes(), media_type=media_type)
    index = FRONTEND_DIST / "index.html"
    return Response(content=index.read_bytes(), media_type="text/html")
