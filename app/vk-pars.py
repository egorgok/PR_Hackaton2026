import argparse
import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx

VK_TOKEN = os.getenv("VK_TOKEN")
VK_API_VERSION = "5.199"
COUNT = 100
API_BASE_URL = "https://api.vk.com/method"


async def vk_api(
    method: str,
    params: dict[str, Any],
    token: str | None = None,
    timeout: float = 20,
) -> dict[str, Any]:
    access_token = token or VK_TOKEN
    if not access_token:
        raise RuntimeError("Укажите переменную окружения VK_TOKEN")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{API_BASE_URL}/{method}",
            params={**params, "access_token": access_token, "v": VK_API_VERSION},
        )
        response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"VK API {method}: {data['error']}")
    return data["response"]


async def get_id(group_id: str, token: str | None = None, timeout: float = 20) -> int:
    result = await vk_api("groups.getById", {"group_id": group_id}, token, timeout)
    groups = result.get("groups", []) if isinstance(result, dict) else result
    if not groups:
        raise RuntimeError("VK API не вернул id сообщества")
    return -int(groups[0]["id"])


async def parse_news(
    owner_id: int,
    token: str | None = None,
    count: int = COUNT,
    timeout: float = 20,
) -> list[dict[str, str]]:
    result = await vk_api(
        "wall.get",
        {
            "owner_id": owner_id,
            "count": min(max(1, count), COUNT),
            "filter": "owner",
            "extended": 0,
        },
        token,
        timeout,
    )
    news = []
    for post in result.get("items", []):
        news.append(
            {
                "date": datetime.fromtimestamp(post["date"], tz=timezone.utc).isoformat(),
                "text": (post.get("text") or "").strip(),
                "url": f"https://vk.com/wall{post.get('owner_id', owner_id)}_{post['id']}",
            }
        )
    return news


def get_attachment_url(attachment: dict[str, Any]) -> str | None:
    obj = attachment.get(attachment.get("type"), {})

    if attachment.get("type") == "photo":
        sizes = obj.get("sizes", [])
        return sizes[-1]["url"] if sizes else None

    if attachment.get("type") == "video":
        return f"https://vk.com/video{obj.get('owner_id')}_{obj.get('id')}"

    if attachment.get("type") == "link":
        return obj.get("url")

    return None


async def _main(group_id: str) -> None:
    owner_id = await get_id(group_id)
    news = await parse_news(owner_id)
    print(f"Получено публикаций: {len(news)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("group_id", help="ID сообщества или короткий адрес, например tubinka")
    asyncio.run(_main(parser.parse_args().group_id))
