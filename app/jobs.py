import asyncio
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobManager:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: set[asyncio.Task] = set()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            rows = connection.execute(
                "SELECT job_id, data_json FROM jobs WHERE json_extract(data_json, '$.status') "
                "IN ('queued', 'running')"
            ).fetchall()
            for row in rows:
                job = json.loads(row["data_json"])
                job["status"] = "interrupted"
                job["updated_at"] = datetime.now(timezone.utc).isoformat()
                for source in job["sources"]:
                    if source["status"] in {"queued", "processing"}:
                        source["status"] = "interrupted"
                        source["message"] = "Поиск прерван перезапуском сервера."
                connection.execute(
                    "UPDATE jobs SET data_json = ?, updated_at = ? WHERE job_id = ?",
                    (json.dumps(job, ensure_ascii=False), job["updated_at"], row["job_id"]),
                )

    def _save(self, job_id: str, owner_id: str, job: dict[str, Any]) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO jobs(job_id, owner_id, data_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (
                    job_id,
                    owner_id,
                    json.dumps(job, ensure_ascii=False),
                    job["updated_at"],
                ),
            )

    async def create(self, payload: dict[str, Any], owner_id: str) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        job = {
            "job_id": job_id,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
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
        self._save(job_id, owner_id, job)
        return job_id

    def spawn(self, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def mutate(self, job_id: str, update) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT owner_id, data_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return
        job = json.loads(row["data_json"])
        update(job)
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(job_id, row["owner_id"], job)

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

    async def snapshot(
        self, job_id: str, owner_id: str | None = None
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            if owner_id is None:
                row = connection.execute(
                    "SELECT data_json FROM jobs WHERE job_id = ?", (job_id,)
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT data_json FROM jobs WHERE job_id = ? AND owner_id = ?",
                    (job_id, owner_id),
                ).fetchone()
        return json.loads(row["data_json"]) if row else None

    async def history(self, owner_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT data_json FROM jobs WHERE owner_id = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (owner_id, limit),
            ).fetchall()
        jobs = [json.loads(row["data_json"]) for row in rows]
        return [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "query": job["query"],
                "days": job["days"],
                "total_sources": job["total_sources"],
                "processed_sources": job["processed_sources"],
                "count": job["count"],
                "excluded_undated_count": job["excluded_undated_count"],
                "status_url": f"/jobs/{job['job_id']}",
                "export_url": f"/jobs/{job['job_id']}/export.xlsx",
            }
            for job in jobs
        ]

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
