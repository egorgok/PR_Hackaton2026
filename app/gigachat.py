import asyncio
import json
import time
import uuid

import httpx

from app.settings import Settings


class GigaChat:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.gigachat_auth_key)

    async def classify(self, query: str, candidates: list[dict[str, str]]) -> set[str]:
        if not self.enabled or not candidates:
            return set()
        token = await self._access_token()
        prompt_data = [{"id": item["id"], "text": item["text"][:2500]} for item in candidates]
        prompt = (
            "Определи, какие публикации относятся к запросу. Считай пересказ и сокращенную "
            "версию того же события подходящими, а совпадение только общих слов — нет. "
            "Верни только JSON вида {\"relevant_ids\":[\"id\"]}. "
            f"Запрос: {query[:2000]}\nПубликации: {json.dumps(prompt_data, ensure_ascii=False)}"
        )
        async with httpx.AsyncClient(timeout=self.settings.gigachat_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.gigachat_api_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "model": self.settings.gigachat_model,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("GigaChat вернул ответ без JSON relevant_ids.")
        result = json.loads(content[start : end + 1])
        return {str(value) for value in result.get("relevant_ids", [])}

    async def _access_token(self) -> str:
        if self._token and self._token_expires_at > time.time() + 30:
            return self._token
        async with self._token_lock:
            if self._token and self._token_expires_at > time.time() + 30:
                return self._token
            request_id = str(uuid.uuid4())
            async with httpx.AsyncClient(timeout=self.settings.gigachat_timeout_seconds) as client:
                response = await client.post(
                    self.settings.gigachat_auth_url,
                    headers={
                        "Authorization": f"Basic {self.settings.gigachat_auth_key}",
                        "RqUID": request_id,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"scope": self.settings.gigachat_scope},
                )
                response.raise_for_status()
            body = response.json()
            self._token = body["access_token"]
            expires_at = float(body.get("expires_at", time.time() + 1800))
            self._token_expires_at = expires_at / 1000 if expires_at > 10**12 else expires_at
            return self._token
