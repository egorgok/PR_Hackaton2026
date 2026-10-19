import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any


class JobManager:
    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()

    async def create(self, payload: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        async with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "query": payload["text"],
                "days": payload["days"],
                "keywords": payload["keywords"],
                "total_sources": len(payload["sources"]),
                "processed_sources": 0,
                "count": 0,
                "excluded_undated_count": 0,
                "results": [],
                "sources": payload["source_states"],
                "errors": [],
            }
        return job_id

    def spawn(self, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def mutate(self, job_id: str, update) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            update(job)
            job["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def add_results(self, job_id: str, results: list[dict[str, Any]]) -> None:
        if not results:
            return

        def apply(job):
            known_urls = {item["url"] for item in job["results"]}
            for result in results:
                if result["url"] not in known_urls:
                    job["results"].append(result)
                    known_urls.add(result["url"])
            job["count"] = len(job["results"])

        await self.mutate(job_id, apply)

    async def snapshot(self, job_id: str) -> dict[str, Any] | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                **job,
                "results": list(job["results"]),
                "sources": [dict(source) for source in job["sources"]],
                "errors": list(job["errors"]),
            }

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
