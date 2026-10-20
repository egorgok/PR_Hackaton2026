import json
import re
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field


class AIClassifier(ABC):
    provider: str

    @property
    @abstractmethod
    def enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def classify(self, query: str, candidates: list[dict[str, str]]) -> set[str]:
        raise NotImplementedError


class YandexGPTDecision(BaseModel):
    id: str
    relevant: bool
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str = ""
    matched_concepts: list[str] = Field(default_factory=list)


class YandexGPTClient(AIClassifier):
    provider = "YandexGPT"

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def expand_query(self, query: str) -> list[str]:
        prompt = (
            "Расшири русский поисковый запрос. Верни только JSON-массив строк. "
            "Включи исходные понятия, синонимы, словоформы и естественные перефразы. "
            "Не добавляй несвязанные общие слова. "
            f"Запрос: {query[:2000]}"
        )
        result = await self._generate(prompt)
        if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
            raise ValueError("YandexGPT вернул неподдерживаемое расширение запроса")
        return list(dict.fromkeys(result))[:40]

    async def classify_detailed(
        self, query: str, candidates: list[dict[str, str]]
    ) -> list[YandexGPTDecision]:
        if not candidates:
            return []
        prompt_data = [{"id": item["id"], "text": item["text"][:2500]} for item in candidates]
        prompt = (
            "Проверь смысловую релевантность публикаций запросу. Верни только JSON-массив "
            'объектов вида {"id":"1","relevant":true,"confidence":0.9,'
            '"reason":"...","matched_concepts":["..."]}. '
            "Учитывай перефразирование и тот же факт, но отклоняй совпадение только по "
            "общим словам. "
            f"Запрос: {query[:2000]}\nПубликации: "
            f"{json.dumps(prompt_data, ensure_ascii=False)}"
        )
        result = await self._generate(prompt)
        if not isinstance(result, list):
            raise ValueError("YandexGPT вернул не массив классификации")
        return [YandexGPTDecision.model_validate(item) for item in result]

    async def classify(self, query: str, candidates: list[dict[str, str]]) -> set[str]:
        return {
            item.id
            for item in await self.classify_detailed(query, candidates)
            if item.relevant
        }

    async def _generate(self, prompt: str) -> object:
        endpoint = self.base_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        body = {
            "modelUri": self.model,
            "completionOptions": {
                "stream": False,
                "temperature": 0,
                "maxTokens": 2000,
            },
            "messages": [{"role": "user", "text": prompt}],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
        content = response.json()["result"]["alternatives"][0]["message"]["text"]
        cleaned = content.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"YandexGPT вернул неподдерживаемый JSON: {content[:300]!r}") from exc


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
