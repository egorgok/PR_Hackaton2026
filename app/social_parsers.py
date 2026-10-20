import asyncio
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.parsers import Candidate, _canonical, _date


def _vk_slug(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[0]


async def fetch_vk(source_url: str, token: str, days: int, limit: int, timeout: float):
    if not token:
        raise RuntimeError("VK_TOKEN не настроен")
    slug = _vk_slug(source_url)
    async with httpx.AsyncClient(timeout=timeout) as client:
        common = {"access_token": token, "v": "5.199"}
        group_response = await client.get(
            "https://api.vk.com/method/groups.getById",
            params={**common, "group_id": slug},
        )
        group_response.raise_for_status()
        group_payload = group_response.json()
        if "error" in group_payload:
            raise RuntimeError(str(group_payload["error"]))
        groups = group_payload.get("response", {}).get("groups", [])
        if not groups:
            groups = group_payload.get("response", [])
        if not groups:
            raise RuntimeError("VK API не вернул id сообщества")
        owner_id = -int(groups[0]["id"])
        response = await client.get(
            "https://api.vk.com/method/wall.get",
            params={
                **common,
                "owner_id": owner_id,
                "count": min(limit, 100),
                "filter": "owner",
            },
        )
        response.raise_for_status()
        payload = response.json()
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = []
    for post in payload.get("response", {}).get("items", []):
        published = datetime.fromtimestamp(post["date"], tz=timezone.utc)
        text = (post.get("text") or "").strip()
        if text and published >= cutoff:
            result.append(
                Candidate(
                    text.splitlines()[0][:160],
                    f"https://vk.com/wall{post.get('owner_id')}_{post.get('id')}",
                    text[:8000],
                    published,
                )
            )
    return result


def _parse_ok_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = _date(value)
    if parsed:
        return parsed
    now = datetime.now(timezone.utc)
    lowered = value.casefold()
    match = re.search(r"([01]?\d|2[0-3]):([0-5]\d)", value)
    hour, minute = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
    if "сегодня" in lowered:
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if "вчера" in lowered:
        return (now - timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
    match = re.search(
        r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})(?:[./-](?P<year>20\d{2}))?",
        value,
    )
    if not match:
        return None
    return datetime(
        int(match.group("year") or now.year),
        int(match.group("month")),
        int(match.group("day")),
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def _parse_ok_html(html: str, base_url: str) -> list[Candidate]:
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for post in soup.select("div.feed"):
        text_node = post.select_one(".media-text_cnt, .media-text")
        text = text_node.get_text(" ", strip=True) if text_node else post.get_text(" ", strip=True)
        if len(text) < 20:
            continue
        date_node = post.select_one("time")
        published = _parse_ok_date(date_node.get_text(" ", strip=True) if date_node else None)
        post_id = post.get("data-post-id") or abs(hash(text))
        result.append(
            Candidate(
                text.splitlines()[0][:160],
                _canonical(f"{base_url}?post={post_id}"),
                text[:8000],
                published,
            )
        )
    return result


async def fetch_ok(browser, source_url: str, days: int, limit: int, timeout: float):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
    )
    page = await context.new_page()
    try:
        await page.goto(source_url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
        await page.wait_for_selector("div.feed", timeout=5000)
        stable = previous = 0
        for _ in range(12):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(700)
            current = await page.locator("div.feed").count()
            stable = stable + 1 if current == previous else 0
            previous = current
            if stable >= 2 or current >= limit:
                break
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [
            item for item in _parse_ok_html(await page.content(), source_url)
            if item.published_at and item.published_at >= cutoff
        ][:limit]
    finally:
        await context.close()


async def stream_social_sources(
    sources, days, limit, timeout, vk_token, concurrency, on_ready, on_error
):
    semaphore = asyncio.Semaphore(concurrency)

    async def one(source, browser=None):
        async with semaphore:
            try:
                candidates = (
                    await fetch_vk(source["url"], vk_token or "", days, limit, timeout)
                    if source["platform"] == "vk"
                    else await fetch_ok(browser, source["url"], days, limit, timeout)
                )
                await on_ready(source, candidates)
            except Exception as exc:
                await on_error(source, exc)

    ok_sources = [source for source in sources if source["platform"] == "ok"]
    vk_sources = [source for source in sources if source["platform"] == "vk"]
    if not ok_sources:
        await asyncio.gather(*(one(source) for source in vk_sources))
        return
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            await asyncio.gather(
                *(one(source, browser) for source in ok_sources),
                *(one(source) for source in vk_sources),
            )
        finally:
            await browser.close()
