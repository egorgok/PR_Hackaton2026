import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.gigachat import GigaChat
from app.ai_client import OpenAICompatibleClient
from app.jobs import JobManager
from app.keywords import extract_keywords, lexical_match
from app.models import Platform, Publication, SearchRequest
from app.parsers import (
    Candidate,
    CaptchaDetected,
    SourceBlocked,
    SourceUnreadable,
    parse_source,
)
from app.registry import Source, SourceRegistry
from app.settings import Settings
from app.social_parsers import stream_social_sources


def filter_by_period(
    candidates: list[Candidate],
    days: int,
    now: datetime | None = None,
) -> tuple[list[Candidate], int]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=days)
    undated = sum(candidate.published_at is None for candidate in candidates)
    matching = [
        candidate
        for candidate in candidates
        if candidate.published_at is not None and cutoff <= candidate.published_at <= current_time
    ]
    return matching, undated


class SearchService:
    def __init__(self, registry: SourceRegistry, jobs: JobManager, settings: Settings):
        self.registry = registry
        self.jobs = jobs
        self.settings = settings
        self.gigachat = GigaChat(settings)
        self.ai_client = OpenAICompatibleClient(
            settings.ai_api_key,
            settings.ai_base_url,
            settings.ai_model,
            settings.ai_timeout_seconds,
        )
        self._gigachat_unavailable = False

    async def start(
        self,
        request: SearchRequest,
        selected: list[Source | dict[str, str]],
        owner_id: str,
    ):
        keywords = extract_keywords(request.text)
        if self.ai_client.enabled:
            try:
                expanded = await self.ai_client.expand_query(request.text)
                keywords = list(
                    dict.fromkeys(
                        keywords + extract_keywords(" ".join(expanded), limit=100)
                    )
                )
            except Exception:
                pass
        source_states = [
            {
                "editor": source.editor if isinstance(source, Source) else source["editor"],
                "platform": source.platform.value
                if isinstance(source, Source)
                else source["platform"],
                "url": source.url if isinstance(source, Source) else source["url"],
                "status": "queued" if isinstance(source, Source) else "unavailable",
                "message": None if isinstance(source, Source) else source["message"],
                "found": 0,
                "undated": 0,
            }
            for source in selected
        ]
        job_id = await self.jobs.create(
            {
                "text": request.text,
                "days": request.days,
                "keywords": keywords,
                "sources": selected,
                "source_states": source_states,
                "ai_mode": (
                    "ai_pending" if self.ai_client.enabled
                    else "gigachat_pending" if self.gigachat.enabled
                    else "lexical_only"
                ),
            },
            owner_id,
        )
        self.jobs.spawn(self._run(job_id, request, selected, keywords))
        return {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"}

    async def _run(self, job_id: str, request: SearchRequest, selected, keywords: list[str]):
        await self.jobs.mutate(job_id, lambda job: job.update(status="running"))
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_sources)
        ai_semaphore = asyncio.Semaphore(3)
        social_sources = [
            {
                "index": index,
                "editor": source.editor,
                "platform": source.platform.value,
                "url": source.url,
            }
            for index, source in enumerate(selected)
            if isinstance(source, Source) and source.platform in {Platform.vk, Platform.ok}
        ]
        social_indexes = {source["index"] for source in social_sources}
        for social_index in social_indexes:
            await self.jobs.mutate(
                job_id,
                lambda job, source_index=social_index: job["sources"][source_index].update(
                    status="processing"
                ),
            )

        async def social_ready(source_data, candidates):
            index = source_data["index"]
            source = selected[index]
            await self._process_candidates(
                job_id, request, source, index, candidates, keywords, ai_semaphore
            )

        async def social_error(source_data, exc):
            await self._source_error(
                job_id,
                source_data["index"],
                "error",
                f"Ошибка {source_data['platform'].upper()}: {type(exc).__name__}",
            )

        if social_sources:
            social_task = asyncio.create_task(
                stream_social_sources(
                    social_sources,
                    request.days,
                    self.settings.max_candidates_per_source * 4,
                    self.settings.source_timeout_seconds,
                    self.settings.vk_token,
                    min(4, self.settings.max_concurrent_sources),
                    social_ready,
                    social_error,
                )
            )
        else:
            social_task = None

        async def handle(index: int, source_or_error):
            if isinstance(source_or_error, dict):
                await self.jobs.mutate(
                    job_id,
                    lambda job: job["sources"][index].update(
                        status="unavailable", message=source_or_error["message"]
                    ),
                )
                await self.jobs.mutate(
                    job_id, lambda job: job.update(processed_sources=job["processed_sources"] + 1)
                )
                return
            source: Source = source_or_error
            if index in social_indexes:
                return
            await self.jobs.mutate(
                job_id, lambda job: job["sources"][index].update(status="processing")
            )
            async with semaphore:
                try:
                    candidates = await asyncio.wait_for(
                        parse_source(
                            source,
                            self.settings.source_timeout_seconds,
                            self.settings.max_candidates_per_source,
                        ),
                        timeout=self.settings.source_timeout_seconds + 2,
                    )
                except CaptchaDetected as exc:
                    await self._source_error(job_id, index, "unavailable", f"Недоступно: CAPTCHA ({exc})")
                    return
                except SourceBlocked as exc:
                    await self._source_error(job_id, index, "unavailable", f"Недоступно: {exc}")
                    return
                except SourceUnreadable as exc:
                    await self._source_error(job_id, index, "unavailable", str(exc))
                    return
                except asyncio.TimeoutError:
                    await self._source_error(job_id, index, "timeout", "Превышено время ожидания источника.")
                    return
                except httpx.TimeoutException:
                    await self._source_error(
                        job_id, index, "timeout", "Превышено время ожидания источника."
                    )
                    return
                except Exception as exc:
                    await self._source_error(job_id, index, "error", f"Ошибка получения: {type(exc).__name__}")
                    return

            await self._process_candidates(
                job_id, request, source, index, candidates, keywords, ai_semaphore
            )

        await asyncio.gather(*(handle(index, source) for index, source in enumerate(selected)))
        if social_task:
            await social_task

        def finish(job: dict[str, Any]):
            statuses = [source["status"] for source in job["sources"]]
            if all(status in ("completed", "no_results") for status in statuses):
                job["status"] = "completed"
            elif any(status in ("completed", "no_results") for status in statuses):
                job["status"] = "completed_with_errors"
            else:
                job["status"] = "failed"

        await self.jobs.mutate(job_id, finish)

    async def _process_candidates(
        self, job_id, request, source, index, candidates, keywords, ai_semaphore
    ):
        candidates, undated_count = filter_by_period(candidates, request.days)
        if not candidates:
            await self._source_done(job_id, index, 0, undated=undated_count)
            return

        relevant: list[tuple[Candidate, str, object | None]] = []
        lexical = [
            (candidate, "lexical")
            for candidate in candidates
            if lexical_match(candidate.title + " " + candidate.text, keywords)
        ]
        if self.ai_client.enabled:
                # AI must see candidates missed by exact lexical matching too.
                preselected = candidates[: self.settings.max_candidates_per_source]
                try:
                    async with ai_semaphore:
                        decisions = await self.ai_client.classify_detailed(
                            request.text,
                            [
                                {"id": str(candidate_index),
                                 "text": candidate.title + "\n" + candidate.text[:2500]}
                                for candidate_index, candidate in enumerate(preselected)
                            ],
                        )
                    decision_by_id = {decision.id: decision for decision in decisions}
                    relevant = [
                        (candidate, "yandexgpt", decision_by_id[str(candidate_index)])
                        for candidate_index, candidate in enumerate(preselected)
                        if str(candidate_index) in decision_by_id
                        and decision_by_id[str(candidate_index)].relevant
                    ]
                    await self.jobs.mutate(job_id, lambda job: job.update(ai_mode="custom_ai"))
                except Exception as exc:
                    relevant = [(candidate, "lexical", None) for candidate, _ in lexical]
                    await self.jobs.mutate(
                        job_id,
                        lambda job: (
                            job.update(ai_mode="lexical_fallback", ai_error=type(exc).__name__),
                            job["errors"].append(
                                f"AI-провайдер недоступен ({type(exc).__name__}); "
                                "для задания включен лексический отбор."
                            ),
                        ),
                    )
        elif self.gigachat.enabled and not self._gigachat_unavailable:
                to_classify = candidates[: self.settings.max_candidates_per_source]
                try:
                    async with ai_semaphore:
                        accepted = await self.gigachat.classify(
                            request.text,
                            [
                                {
                                    "id": str(index),
                                    "text": candidate.title + "\n" + candidate.text[:2500],
                                }
                                for index, candidate in enumerate(to_classify)
                            ],
                        )
                    await self.jobs.mutate(job_id, lambda job: job.update(ai_mode="gigachat"))
                    relevant = [
                        (candidate, "gigachat", None)
                        for index, candidate in enumerate(to_classify)
                        if str(index) in accepted
                    ]
                except Exception as exc:
                    relevant = [(candidate, "lexical", None) for candidate, _ in lexical]
                    # Do not wait for the same unreachable API once per source.
                    # The lexical fallback remains available for the rest of the job.
                    self._gigachat_unavailable = True
                    if isinstance(exc, httpx.HTTPStatusError):
                        error_detail = f"HTTP {exc.response.status_code}"
                    elif isinstance(exc, httpx.HTTPError):
                        error_detail = f"{type(exc).__name__}: {exc}"
                    else:
                        error_detail = type(exc).__name__
                    await self.jobs.mutate(
                        job_id,
                        lambda job: (
                            job.update(ai_mode="lexical_fallback", ai_error=error_detail),
                            job["errors"].append(
                                f"GigaChat недоступен ({error_detail}); "
                                "для задания включен лексический отбор."
                            ),
                        ),
                    )
        else:
            relevant = [(candidate, "lexical", None) for candidate, _ in lexical]

        publications = [
                Publication(
                    editor=source.editor,
                    platform=source.platform,
                    source_name=source.host,
                    title=candidate.title or candidate.text[:160],
                    url=candidate.url,
                    excerpt=candidate.text[:450],
                    published_at=candidate.published_at,
                    date_status="within_period" if candidate.published_at else "unknown",
                    relevance=(
                        "Смысловое совпадение"
                    if method in {"gigachat", "custom_ai"}
                        else "Совпадение ключевых слов"
                    ),
                    match_method=method,
                ).model_dump(mode="json")
                for candidate, method, decision in relevant
        ]
        await self.jobs.add_results(job_id, publications)
        await self._source_done(job_id, index, len(publications), undated=undated_count)

    async def _source_error(self, job_id: str, index: int, status: str, message: str):
        def update(job: dict[str, Any]):
            job["sources"][index].update(status=status, message=message)
            job["processed_sources"] += 1
            job["errors"].append(message)

        await self.jobs.mutate(job_id, update)

    async def _source_done(self, job_id: str, index: int, found: int, undated: int = 0):
        def update(job: dict[str, Any]):
            job["sources"][index].update(
                status="completed" if found else "no_results",
                found=found,
                undated=undated,
                message=(
                    None
                    if found
                    else (
                        "Материалы с неизвестной датой исключены: попадание в период не подтверждено."
                        if undated
                        else "Подходящие публикации не найдены."
                    )
                ),
            )
            job["processed_sources"] += 1
            job["excluded_undated_count"] += undated

        await self.jobs.mutate(job_id, update)
