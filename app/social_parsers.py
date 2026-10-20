import asyncio
import importlib.util
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.parsers import Candidate, _canonical, _date


def _vk_slug(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[0]


def _load_vk_parser():
    module_path = Path(__file__).with_name("vk-pars.py")
    spec = importlib.util.spec_from_file_location("project_vk_parser", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить {module_path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def fetch_vk(
    source_url: str,
    token: str,
    days: int,
    limit: int,
    timeout: float,
    on_batch=None,
    batch_size: int = 25,
):
    if not token:
        raise RuntimeError("VK_TOKEN не настроен")
    parser = _load_vk_parser()
    owner_id = await asyncio.wait_for(
        parser.get_id(_vk_slug(source_url), token=token, timeout=timeout),
        timeout=timeout + 1,
    )
    posts = await asyncio.wait_for(
        parser.parse_news(owner_id, token=token, count=min(limit, 100), timeout=timeout),
        timeout=timeout + 1,
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result: list[Candidate] = []
    batch: list[Candidate] = []
    for post in posts[:limit]:
        published = datetime.fromisoformat(post["date"])
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        published = published.astimezone(timezone.utc)
        text = (post.get("text") or "").strip()
        if text and published >= cutoff:
            candidate = Candidate(text.splitlines()[0][:160], post["url"], text[:8000], published)
            if on_batch:
                batch.append(candidate)
                if len(batch) >= batch_size:
                    await on_batch(list(batch))
                    batch.clear()
            else:
                result.append(candidate)
    if on_batch and batch:
        await on_batch(list(batch))
    return [] if on_batch else result


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
            item
            for item in _parse_ok_html(await page.content(), source_url)
            if item.published_at and item.published_at >= cutoff
        ][:limit]
    finally:
        await context.close()


async def stream_social_sources(
    sources,
    days,
    limit,
    timeout,
    vk_token,
    concurrency,
    on_ready,
    on_error,
    on_complete=None,
):
    semaphore = asyncio.Semaphore(concurrency)

    async def one(source, browser=None):
        async with semaphore:
            try:
                if source["platform"] == "vk":
                    candidates = await fetch_vk(
                        source["url"],
                        vk_token or "",
                        days,
                        limit,
                        timeout,
                        on_batch=lambda batch: on_ready(source, batch),
                    )
                else:
                    candidates = await fetch_ok(browser, source["url"], days, limit, timeout)
                    await on_ready(source, candidates)
                if on_complete:
                    await on_complete(source)
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
