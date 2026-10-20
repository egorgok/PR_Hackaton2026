import asyncio
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.models import Platform
from app.registry import Source

USER_AGENT = (
    "MediaMonitorPrototype/0.1 (+public-content monitoring; "
    "contact: configure a responsible contact before deployment)"
)
CAPTCHA_MARKERS = ("captcha", "verify you are human", "robot check", "проверка что вы не робот")
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?:[t ][0-9:.+\-z]+)?\b", re.I)
RU_DATE_RE = re.compile(
    r"\b(?P<day>[0-3]?\d)\s+(?P<month>января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря)(?:\s+(?P<year>20\d{2}))?"
    r"(?:[,\s]+(?P<hour>[0-2]?\d):(?P<minute>[0-5]\d))?",
    re.I,
)
RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
SKIP_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp4", ".zip", ".svg")
NON_ARTICLE_SEGMENTS = {
    "about", "authors", "category", "contacts", "feed", "page", "search",
    "tag", "tags", "theme", "themes", "topics", "rubric", "rubrics",
}
NEWS_SECTION_MARKERS = (
    "news", "novost", "новост", "article", "articles", "publ", "rubric",
    "category", "topic", "material", "press",
)
COMMON_NEWS_SECTION_PATHS = (
    "/news/",
    "/novosti/",
    "/новости/",
    "/articles/",
    "/publ/",
    "/rubric/",
    "/category/",
    "/press/",
)


@dataclass
class Candidate:
    title: str
    url: str
    text: str
    published_at: datetime | None


class CaptchaDetected(Exception):
    pass


class SourceBlocked(Exception):
    pass

class SourceUnreadable(Exception):
    pass


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            match = DATE_RE.search(value)
            if not match:
                ru_match = RU_DATE_RE.search(value.casefold())
                if not ru_match:
                    return None
                year_text = ru_match.group("year")
                year = int(year_text or datetime.now(timezone.utc).year)
                parsed = datetime(
                    year,
                    RU_MONTHS[ru_match.group("month")],
                    int(ru_match.group("day")),
                    int(ru_match.group("hour") or 0),
                    int(ru_match.group("minute") or 0),
                    tzinfo=timezone.utc,
                )
                if not year_text and parsed > datetime.now(timezone.utc):
                    parsed = parsed.replace(year=parsed.year - 1)
            else:
                try:
                    parsed = datetime.fromisoformat(match.group().replace("z", "+00:00"))
                except ValueError:
                    return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical(url: str) -> str:
    parts = urlparse(url)
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in {"fbclid", "gclid", "yclid"}
        ]
    )
    return urlunparse(
        (parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", query, "")
    )


def _article_date(soup: BeautifulSoup) -> datetime | None:
    for selector, attribute in (
        ("meta[property='article:published_time']", "content"),
        ("meta[name='date']", "content"),
        ("meta[name='pubdate']", "content"),
        ("meta[name='publish_date']", "content"),
        ("meta[itemprop='datePublished']", "content"),
        ("time[datetime]", "datetime"),
    ):
        node = soup.select_one(selector)
        if node:
            value = _date(node.get(attribute))
            if value:
                return value
    for selector in ("time", "[class*='date']", "[class*='published']", "[class*='datetime']"):
        for node in soup.select(selector)[:20]:
            value = _date(node.get_text(" ", strip=True))
            if value:
                return value
    for node in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(node.string or node.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        for item in stack:
            if not isinstance(item, dict):
                continue
            if item.get("@graph"):
                stack.extend(item["@graph"])
            value = _date(item.get("datePublished") or item.get("dateCreated"))
            if value:
                return value
    return None


def _text(node: BeautifulSoup) -> str:
    for unwanted in node.select("script, style, nav, footer, header, form, button, aside"):
        unwanted.decompose()
    return " ".join(node.stripped_strings)


def _extract_posts(soup: BeautifulSoup, base_url: str, platform: Platform) -> list[Candidate]:
    candidates: list[Candidate] = []
    selectors = {
        Platform.telegram: ".tgme_widget_message",
        Platform.vk: "[data-post-id], .wall_post",
        Platform.ok: "[data-post-id], .feed",
        Platform.max: "article, [class*='post'], [class*='message']",
        Platform.zen: "article, [class*='article'], [class*='feed']",
        Platform.website: (
            "article, [itemtype*='Article'], "
            "[class*='news-item'], [class*='post-item'], [class*='article-item']"
        ),
    }
    for node in soup.select(selectors[platform])[:100]:
        text = _text(node)
        if len(text) < 40:
            continue
        link = node.select_one("a[href*='/status/'], a[href*='/wall'], a[href*='/posts/'], a[href]")
        href = link.get("href") if link else None
        if platform == Platform.telegram:
            href_node = node.select_one(".tgme_widget_message_date")
            href = href_node.get("href") if href_node else href
        url = urljoin(base_url, href or "")
        if not href:
            url = base_url
        title_node = node.select_one("h1, h2, h3, [class*='title']")
        title = title_node.get_text(" ", strip=True) if title_node else text[:160]
        published = _article_date(node)
        candidates.append(Candidate(title, _canonical(url), text[:6000], published))
    return candidates


async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    max_response_bytes = 5 * 1024 * 1024
    async with client.stream("GET", url, follow_redirects=True) as response:
        chunks = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > max_response_bytes:
                raise SourceBlocked("Ответ источника превышает лимит 5 МБ.")
            chunks.append(chunk)
        text = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        final_url = str(response.url)
        status_code = response.status_code
    if any(marker in text[:20000].casefold() for marker in CAPTCHA_MARKERS):
        raise CaptchaDetected("Страница требует CAPTCHA.")
    if status_code in (401, 403, 429):
        raise SourceBlocked(f"HTTP {status_code}")
    if status_code >= 400:
        raise httpx.HTTPStatusError(
            f"HTTP {status_code} for {final_url}",
            request=httpx.Request("GET", final_url),
            response=httpx.Response(status_code, request=httpx.Request("GET", final_url)),
        )
    return final_url, text


def _same_host(source_url: str, link_url: str) -> bool:
    source_host = (urlparse(source_url).hostname or "").casefold()
    link_host = (urlparse(link_url).hostname or "").casefold()
    return bool(source_host and link_host and (link_host == source_host or link_host.endswith(f".{source_host}")))


def _feed_url(soup: BeautifulSoup, page_url: str) -> str | None:
    for node in soup.select("link[rel='alternate'][type*='rss'], link[rel='alternate'][type*='atom']"):
        href = node.get("href")
        if href:
            return urljoin(page_url, href)
    return None


async def _try_common_feeds(
    client: httpx.AsyncClient, page_url: str
) -> list[Candidate]:
    base = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
    paths = ("/rss.xml", "/feed", "/feed/", "/rss", "/rss/", "/atom.xml")
    for path in paths:
        feed_url = urljoin(base, path)
        try:
            final_url, feed_html = await _fetch(client, feed_url)
        except (httpx.HTTPError, SourceBlocked, CaptchaDetected):
            continue
        candidates = _parse_feed(feed_html, final_url)
        if candidates:
            return candidates
    return []


def _parse_feed(xml_text: str, feed_url: str) -> list[Candidate]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    def child_text(element: ElementTree.Element, *names: str) -> str:
        for child in element.iter():
            local_name = child.tag.rsplit("}", 1)[-1].casefold()
            if local_name in names and child.text:
                return child.text.strip()
        return ""

    entries = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].casefold() in ("item", "entry")
    ]
    items: list[Candidate] = []
    for entry in entries:
        title = child_text(entry, "title")
        link = ""
        for node in entry.iter():
            if node.tag.rsplit("}", 1)[-1].casefold() != "link":
                continue
            link = node.get("href") or (node.text or "").strip()
            if link:
                break
        if not link:
            continue
        body = child_text(entry, "encoded", "description", "summary", "content")
        body = BeautifulSoup(html.unescape(body), "html.parser").get_text(" ", strip=True)
        published = _date(child_text(entry, "pubdate", "published", "updated", "date"))
        items.append(
            Candidate(
                title=title or body[:160] or "Заголовок недоступен",
                url=_canonical(urljoin(feed_url, link)),
                text=body or title,
                published_at=published,
            )
        )
    return items


def _is_article_page(soup: BeautifulSoup, url: str, text: str) -> bool:
    path_parts = [part.casefold() for part in urlparse(url).path.split("/") if part]
    if any(part in NON_ARTICLE_SEGMENTS for part in path_parts) or len(text) < 120:
        return False
    if soup.select_one(
        "meta[property='article:published_time'], "
        "meta[itemprop='datePublished'], [itemprop='articleBody']"
    ):
        return True
    if soup.select_one(
        "article, [itemtype*='Article'], [itemtype*='NewsArticle'], "
        "[class*='article-body'], [class*='article-text'], "
        "[class*='news-detail'], [class*='news-body'], [class*='post-content'], "
        "[class*='entry-content']"
    ):
        return True
    og_type = soup.select_one("meta[property='og:type']")
    if og_type and og_type.get("content", "").casefold() == "article":
        return True
    for node in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(node.string or node.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            if item.get("@graph"):
                stack.extend(item["@graph"])
            item_type = item.get("@type", [])
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(
                str(value).casefold() in {"article", "newsarticle", "reportage"}
                for value in types
            ):
                return True
    # Many regional CMS pages omit schema.org markup. A substantial main block
    # with a heading is still a publication unless the URL is clearly an archive.
    return bool(
        soup.select_one(
            "main h1, main h2, .content h1, .article h1, "
            "[class*='news-detail'] h1, [class*='article'] h1"
        )
    ) and len(text) >= 300


async def parse_source(source: Source, timeout: float, max_candidates: int) -> list[Candidate]:
    limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"},
    ) as client:
        start_url = source.url
        if source.platform == Platform.telegram:
            parts = urlparse(source.url)
            handle = parts.path.strip("/")
            if handle and not handle.startswith("s/"):
                start_url = urljoin(source.url, f"/s/{handle}")
        final_url, html = await _fetch(client, start_url)
        soup = BeautifulSoup(html, "html.parser")
        direct_posts = _extract_posts(soup, final_url, source.platform)
        if direct_posts:
            return _dedupe(direct_posts)[:max_candidates]

        article_links: list[str] = []
        feed_candidates: list[Candidate] = []
        if source.platform == Platform.website:
            feed_url = _feed_url(soup, final_url)
            if feed_url:
                try:
                    final_feed_url, feed_html = await _fetch(client, feed_url)
                    feed_candidates = _parse_feed(feed_html, final_feed_url)
                    article_links.extend(item.url for item in feed_candidates)
                except (httpx.HTTPError, SourceBlocked):
                    pass
            if not feed_candidates:
                feed_candidates = await _try_common_feeds(client, final_url)
                article_links.extend(item.url for item in feed_candidates)
        section_links: list[str] = []
        for anchor in soup.select("a[href]"):
            link = urljoin(final_url, anchor.get("href", ""))
            parsed = urlparse(link)
            if parsed.scheme not in ("http", "https") or not _same_host(final_url, link):
                continue
            if parsed.path.lower().endswith(SKIP_EXTENSIONS) or link == final_url:
                continue
            if source.platform == Platform.website:
                if len(parsed.path.strip("/").split("/")) < 1:
                    continue
                anchor_text = anchor.get_text(" ", strip=True).casefold()
                path = parsed.path.casefold()
                if any(marker in path or marker in anchor_text for marker in NEWS_SECTION_MARKERS):
                    section_links.append(_canonical(link))
            elif source.platform == Platform.telegram:
                if "/s/" not in parsed.path and not re.search(r"/[^/]+/\d+$", parsed.path):
                    continue
            else:
                if not any(word in parsed.path for word in ("wall", "status", "post", "article")):
                    continue
            article_links.append(_canonical(link))

        if source.platform == Platform.website:
            site_root = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
            section_links.extend(
                urljoin(site_root, path) for path in COMMON_NEWS_SECTION_PATHS
            )
        if source.platform == Platform.website and section_links:
            section_urls = list(dict.fromkeys(section_links))[:12]

            async def discover_section_links(section_url: str) -> list[str]:
                try:
                    section_final_url, section_html = await _fetch(client, section_url)
                except (httpx.HTTPError, SourceBlocked, CaptchaDetected):
                    return []
                section_soup = BeautifulSoup(section_html, "html.parser")
                discovered: list[str] = []
                for anchor in section_soup.select("a[href]"):
                    link = _canonical(urljoin(section_final_url, anchor.get("href", "")))
                    parsed = urlparse(link)
                    if (
                        parsed.scheme in ("http", "https")
                        and _same_host(final_url, link)
                        and not parsed.path.lower().endswith(SKIP_EXTENSIONS)
                        and link != section_final_url
                    ):
                        discovered.append(link)
                return discovered

            section_results = await asyncio.gather(
                *(discover_section_links(url) for url in section_urls)
            )
            for discovered in section_results:
                article_links.extend(discovered)

        # A section can expose more links than the per-source result limit.
        # Fetch a larger candidate pool, then apply date and AI filtering later.
        links = list(dict.fromkeys(article_links))[: max_candidates * 4]
        semaphore = asyncio.Semaphore(4)

        async def fetch_candidate(link: str) -> Candidate | None:
            async with semaphore:
                try:
                    article_url, article_html = await _fetch(client, link)
                except CaptchaDetected:
                    raise
                except (httpx.HTTPError, SourceBlocked):
                    return None
            article = BeautifulSoup(article_html, "html.parser")
            article_text = article.get_text(" ", strip=True)
            if not _is_article_page(article, article_url, article_text):
                return None
            title_node = article.select_one("h1") or article.select_one("meta[property='og:title']")
            title = (
                title_node.get("content", "").strip()
                if title_node.name == "meta"
                else title_node.get_text(" ", strip=True)
                if title_node
                else ""
            )
            content_node = (
                article.select_one("article")
                or article.select_one("[itemprop='articleBody']")
                or article.select_one("main")
                or article.select_one(
                    "[class*='article-body'], [class*='article-text'], "
                    "[class*='news-detail'], [class*='news-body'], "
                    "[class*='post-content'], [class*='entry-content']"
                )
            )
            if content_node is None:
                return None
            text = _text(content_node)
            if len(text) < 80:
                return None
            return Candidate(title or text[:160], _canonical(article_url), text[:8000], _article_date(article))

        tasks = [fetch_candidate(link) for link in links]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)
        if any(isinstance(item, CaptchaDetected) for item in fetched):
            raise CaptchaDetected("Одна или несколько страниц источника требуют CAPTCHA.")
        candidates = [item for item in fetched if isinstance(item, Candidate)]
        fetched_urls = {item.url for item in candidates}
        candidates.extend(item for item in feed_candidates if item.url not in fetched_urls)
        if not candidates and direct_posts:
            candidates = direct_posts
        if not candidates:
            # The page was reachable and was not blocked. It is a valid empty
            # result, not an unavailable source.
            return []
        return _dedupe(candidates)[:max_candidates]


def _dedupe(items: list[Candidate]) -> list[Candidate]:
    unique: dict[str, Candidate] = {}
    for item in items:
        if item.url and item.url not in unique:
            unique[item.url] = item
    return list(unique.values())
