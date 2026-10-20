import json
import re
from abc import ABC, abstractmethod

import httpx


class AIClassifier(ABC):
    provider: str

    @property
    @abstractmethod
    def enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def classify(self, query: str, candidates: list[dict[str, str]]) -> set[str]:
        raise NotImplementedError


class GeminiClient(AIClassifier):
    provider = "Gemini"

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def classify(self, query: str, candidates: list[dict[str, str]]) -> set[str]:
        prompt_data = [{"id": item["id"], "text": item["text"][:2500]} for item in candidates]
        prompt = (
            "Определи, какие публикации относятся к запросу. Учитывай перефразирование "
            "и тот же факт, но отклоняй совпадение только по общим словам. "
            'Верни только JSON вида {"relevant_ids":["id"]}. '
            f"Запрос: {query[:2000]}\nПубликации: "
            f"{json.dumps(prompt_data, ensure_ascii=False)}"
        )
        endpoint = f"{self.base_url}/models/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key,
        }
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            if response.status_code == 400:
                # Some Gemini model aliases/accounts reject structured output
                # even though normal generateContent is available.
                body["generationConfig"].pop("responseMimeType", None)
                response = await client.post(endpoint, headers=headers, json=body)
            if response.is_error:
                detail = response.text[:1000].replace("\n", " ")
                raise httpx.HTTPStatusError(
                    f"Gemini HTTP {response.status_code}: {detail}",
                    request=response.request,
                    response=response,
                )
        content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return set(OpenAICompatibleClient._parse_ids(content))


class OpenAICompatibleClient(AIClassifier):
    provider = "Deep" + "Seek"

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def classify(self, query: str, candidates: list[dict[str, str]]) -> set[str]:
        prompt_data = [{"id": item["id"], "text": item["text"][:2500]} for item in candidates]
        prompt = (
            "Определи, какие публикации относятся к запросу. Учитывай перефразирование "
            "и тот же факт, но отклоняй совпадение только по общим словам. "
            'Верни только JSON вида {"relevant_ids":["id"]}. '
            f"Запрос: {query[:2000]}\nПубликации: "
            f"{json.dumps(prompt_data, ensure_ascii=False)}"
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0,
                    "stream": False,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты классификатор релевантности новостных публикаций.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return set(self._parse_ids(content))

    @staticmethod
    def _parse_ids(content: str) -> list[str]:
        cleaned = content.strip().replace("```json", "").replace("```", "").strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        candidates = [cleaned]
        if start >= 0 and end > start:
            candidates.append(cleaned[start : end + 1])
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and isinstance(payload.get("relevant_ids"), list):
                return [str(value) for value in payload["relevant_ids"]]
        match = re.search(r"relevant_ids\s*[:=]\s*\[([^\]]*)\]", cleaned, re.I)
        if match:
            return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
        raise ValueError(f"LLM вернул неподдерживаемый JSON: {content[:300]!r}")
