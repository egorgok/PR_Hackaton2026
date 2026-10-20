import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import httpx
from openpyxl import load_workbook

from app.keywords import extract_keywords, lexical_match
from app.main import app
from app.models import Platform, SearchRequest
from app.parsers import (
    Candidate,
    _article_date,
    _canonical,
    _date,
    _extract_posts,
    _is_article_page,
    _parse_feed,
)
from app.search import filter_by_period
from app.registry import SourceRegistry
from app.settings import Settings
from app.xlsx import build_workbook
from app.jobs import JobManager
from app.gigachat import GigaChat
from app.main import jobs as app_jobs, search_service
import app.social_parsers as social_parsers


def test_vk_api_parser_streams_candidates_in_batches(monkeypatch):
    class Parser:
        async def get_id(self, slug, **kwargs):
            assert slug == "tubinka"
            return -123

        async def parse_news(self, owner_id, **kwargs):
            assert owner_id == -123
            return [
                {
                    "date": "2026-10-20T10:00:00+00:00",
                    "text": f"Публикация VK {index}",
                    "url": f"https://vk.com/wall-123_{index}",
                }
                for index in range(30)
            ]

    monkeypatch.setattr(social_parsers, "_load_vk_parser", lambda: Parser())
    batches = []

    async def append_batch(batch):
        batches.append(batch)

    async def collect():
        return await social_parsers.fetch_vk(
            "https://vk.com/tubinka", "token", 7, 100, 5, on_batch=append_batch
        )

    candidates = asyncio.run(collect())
    assert candidates == []
    assert [len(batch) for batch in batches] == [25, 5]
    assert batches[0][0].url == "https://vk.com/wall-123_0"


def test_registry_loads_and_resolves_table_source():
    registry = SourceRegistry(Settings.from_env().sources_file)
    selected = registry.resolve_selection([Platform.telegram], ["  Авангард "])
    assert len(registry.list_sources()) == 268
    assert selected[0].editor == "Авангард"
    assert selected[0].url == "https://t.me/avangard_online"


def test_registry_marks_missing_platform_without_inventing_url():
    registry = SourceRegistry(Settings.from_env().sources_file)
    selected = registry.resolve_selection([Platform.zen], ["Авангард"])
    assert selected == [
        {
            "editor": "Авангард",
            "platform": "zen",
            "url": "",
            "message": "Для редакции нет адреса на выбранной площадке.",
        }
    ]


def test_registry_can_select_every_registered_source():
    registry = SourceRegistry(Settings.from_env().sources_file)
    selected = registry.all_sources(list(Platform))
    assert len(selected) == 268
    assert len({source.editor for source in selected}) == 48


def test_search_contract_validates_supported_periods():
    request = SearchRequest(
        text="Пожар в школе Красноярска",
        platform=["website", "telegram"],
        editor=["Авангард"],
        days=14,
    )
    assert request.days == 14
    try:
        SearchRequest(text="Новости региона", platform=["website"], editor=["Авангард"], days=2)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported period must be rejected")


def test_keyword_matching_and_canonical_url():
    keywords = extract_keywords("Пожар в школе Красноярска")
    assert "пожар" in keywords
    assert lexical_match("В школе Красноярска произошел пожар", keywords)
    assert not lexical_match("Новая информация о Красноярске", keywords)
    assert not lexical_match("Ремонт школьной дороги", keywords)
    assert _canonical("https://news.example/story/?utm_source=x&id=42#article") == (
        "https://news.example/story?id=42"
    )


def test_feed_parser_returns_direct_links_and_dates():
    feed = """<?xml version="1.0"?><rss><channel><item>
      <title>Событие в регионе</title><link>https://news.example/post-1</link>
      <description><![CDATA[<p>Текст новости.</p>]]></description>
      <pubDate>Mon, 19 Oct 2026 12:00:00 +0000</pubDate>
    </item></channel></rss>"""
    items = _parse_feed(feed, "https://news.example/feed")
    assert len(items) == 1
    assert items[0].url == "https://news.example/post-1"
    assert items[0].published_at == datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


def test_article_date_reads_published_metadata():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        '<meta property="article:published_time" content="2026-10-19T12:00:00Z">',
        "html.parser",
    )
    assert _article_date(soup) == datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    assert _date("19 октября 2026, 14:30") == datetime(
        2026, 10, 19, 14, 30, tzinfo=timezone.utc
    )


def test_gigachat_classification_parser_accepts_json_variants():
    assert GigaChat._parse_classification('{"relevant_ids":["1","3"]}') == ["1", "3"]
    assert GigaChat._parse_classification("```json\n{\"relevant_ids\": [\"2\"]}\n```") == ["2"]
    assert GigaChat._parse_classification("Ответ: relevant_ids: [\"4\"]") == ["4"]


def test_markup_parser_extracts_semantic_news_cards_with_russian_date():
    from bs4 import BeautifulSoup
    from app.models import Platform

    soup = BeautifulSoup(
        "<main><div class='news-item'><a href='/news/42'>Пожар в школе</a>"
        "<time>19 октября 2026, 14:30</time><p>Подробный текст публикации "
        "для проверки разметки источника.</p></div></main>",
        "html.parser",
    )
    items = _extract_posts(soup, "https://news.example/", Platform.website)
    assert len(items) == 1
    assert items[0].url == "https://news.example/news/42"
    assert items[0].published_at == datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)

def test_archive_page_is_not_a_publication_but_article_metadata_is():
    from bs4 import BeautifulSoup

    archive = BeautifulSoup(
        "<html><body><main><h1>Теги и темы</h1><p>"
        + ("Архив тегов. " * 30)
        + "</p></main></body></html>",
        "html.parser",
    )
    article = BeautifulSoup(
        '<html><head><meta property="og:type" content="article"></head>'
        "<body><main><h1>Пожар в школе</h1><p>"
        + ("Текст публикации. " * 30)
        + "</p></main></body></html>",
        "html.parser",
    )
    assert not _is_article_page(archive, "https://news.example/themes", archive.get_text(" "))
    assert _is_article_page(article, "https://news.example/news/123", article.get_text(" "))

def test_unknown_publication_date_is_excluded_from_period_results():
    now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    candidates = [
        Candidate("Unknown date", "https://news.example/unknown", "Text", None),
        Candidate(
            "Inside period",
            "https://news.example/recent",
            "Text",
            datetime(2026, 10, 18, 12, tzinfo=timezone.utc),
        ),
        Candidate(
            "Outside period",
            "https://news.example/old",
            "Text",
            datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
        ),
    ]
    matching, unknown_count = filter_by_period(candidates, 7, now=now)
    assert [candidate.title for candidate in matching] == ["Inside period"]
    assert unknown_count == 1


def test_xlsx_contains_same_publication_and_clickable_url():
    job = {
        "results": [
            {
                "editor": "Редакция",
                "platform": "website",
                "source_name": "Редакция",
                "title": "Заголовок",
                "published_at": None,
                "date_status": "unknown",
                "url": "https://news.example/post",
                "excerpt": "Выдержка",
                "relevance": "Совпадение ключевых слов",
                "match_method": "lexical",
            }
        ],
        "query": "Проверочный запрос",
        "days": 7,
        "keywords": ["проверочный"],
        "count": 1,
        "status": "completed",
        "job_id": "job-id",
    }
    content = build_workbook(job)
    workbook = load_workbook(content, data_only=True)
    assert workbook["Публикации"]["G2"].value == "unknown"
    assert workbook["Параметры поиска"]["B5"].value == 1
    content.seek(0)
    linked_workbook = load_workbook(content, data_only=False)
    assert linked_workbook["Публикации"]["H2"].value == "https://news.example/post"
    assert linked_workbook["Публикации"]["H2"].hyperlink.target == "https://news.example/post"


def test_health_and_source_catalog_endpoints():
    async def check_endpoints():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            catalog = await client.get("/sources")
            assert catalog.status_code == 200
            assert len(catalog.json()["sources"]) == 268

    asyncio.run(check_endpoints())


def test_full_job_uses_all_registry_sources_without_running_network(monkeypatch):
    async def check_full_job():
        monkeypatch.setattr(
            search_service,
            "start",
            AsyncMock(return_value={"job_id": "full-test", "status": "queued"}),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/jobs/all",
                json={"text": "Проверка всего реестра", "days": 1},
            )
            assert response.status_code == 202
            body = response.json()
            assert body["scope"] == "all_registry_sources"
            assert body["selected_sources"] == 268
            assert search_service.start.await_args.args[1].__len__() == 268

    asyncio.run(check_full_job())


def test_job_history_persists_and_is_scoped_to_session(tmp_path):
    async def check_persistence():
        database = tmp_path / "jobs.sqlite3"
        manager = JobManager(database)
        payload = {
            "text": "Запрос для истории",
            "days": 7,
            "keywords": ["история"],
            "sources": [{}],
            "source_states": [{"status": "queued"}],
        }
        job_id = await manager.create(payload, owner_id="browser-session-a")
        await manager.mutate(
            job_id,
            lambda job: job.update(status="completed", processed_sources=1),
        )

        restored = JobManager(database)
        own_job = await restored.snapshot(job_id, "browser-session-a")
        other_job = await restored.snapshot(job_id, "browser-session-b")
        history = await restored.history("browser-session-a")

        assert own_job["status"] == "completed"
        assert other_job is None
        assert len(history) == 1
        assert history[0]["job_id"] == job_id

    asyncio.run(check_persistence())


def test_history_endpoint_sets_http_only_session_cookie():
    async def check_cookie():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/history")
            assert response.status_code == 200
            assert response.json() == {"jobs": []}
            cookie = response.headers["set-cookie"].casefold()
            assert "media_session=" in cookie
            assert "httponly" in cookie
            assert "samesite=lax" in cookie
            assert client.cookies.get("media_session")

    asyncio.run(check_cookie())


def test_browser_can_reopen_and_export_its_saved_job():
    async def check_saved_job():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/history")
            session_id = client.cookies.get("media_session")
            job_id = await app_jobs.create(
                {
                    "text": "Прошлый запрос",
                    "days": 3,
                    "keywords": ["прошлый"],
                    "sources": [],
                    "source_states": [],
                },
                owner_id=session_id,
            )
            await app_jobs.mutate(
                job_id,
                lambda job: job.update(status="completed"),
            )

            history = await client.get("/history")
            details = await client.get(f"/jobs/{job_id}")
            export = await client.get(f"/jobs/{job_id}/export.xlsx")

            assert history.json()["jobs"][0]["job_id"] == job_id
            assert details.json()["query"] == "Прошлый запрос"
            assert export.status_code == 200

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as other:
            assert (await other.get(f"/jobs/{job_id}")).status_code == 404

    asyncio.run(check_saved_job())


