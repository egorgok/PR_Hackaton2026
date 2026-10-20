import asyncio
import datetime
import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from xlsx import build_workbook

# Исходящие параметры конфигурации
INPUT_EXCEL_PATH = (
    r"sources.xlsx"
)

# НАСТРОЙКА СКОРОСТИ: сколько групп Одноклассников парсить ОДНОВРЕМЕННО
CONCURRENT_LIMITERS = 4

def read_links_from_excel(path):
    """Считывает данные из Excel-файла по названиям колонок"""
    try:
        df = pd.read_excel(path)
        df.columns = [str(col).strip() for col in df.columns]
        target_col_name = "Редакция газеты"
        ok_col_name = "ОК"
        data_list = []
        for index, row in df.iterrows():
            name = str(row[target_col_name]).strip()
            ok_url = str(row[ok_col_name]).strip()
            
            if (
                ok_url
                and ok_url.startswith("http")
                and "ok.ru" in ok_url
                and "nan" not in ok_url.lower()
            ):
                data_list.append({"name": name, "url": ok_url})

        return data_list
    except Exception as e:
        print(f"❌ Ошибка чтения исходного Excel: {e}")
        return []


def clean_sheet_name(name):
    """Очищает и обрезает имя вкладки под требования Excel"""
    clean_name = re.sub(r'[\\/*?:\[\]]', "", name)
    return clean_name[:30]


def parse_posts_from_html(html_content):
    """Молниеносный разбор DOM-структуры через BeautifulSoup"""
    soup = BeautifulSoup(html_content, "html.parser")
    posts_elements = soup.find_all("div", class_="feed")
    parsed_posts = []

    for post in posts_elements:
        time_element = post.find("time")
        post_date = (
            time_element.get_text(strip=True) if time_element else "Не указана"
        )

        text_container = post.find(class_="media-text_cnt") or post.find(
            class_="media-text"
        )
        post_title = "Без заголовка"
        post_text = ""

        if text_container:
            title_el = text_container.find(
                class_="media-block_header"
            ) or text_container.find("h3")
            if title_el:
                post_title = title_el.get_text(strip=True)
                title_el.decompose()

            post_text = text_container.get_text(separator="\n", strip=True)

            if (
                post_title == "Без заголовка" or not post_title
            ) and post_text:
                lines = [
                    line.strip() for line in post_text.split("\n") if line.strip()
                ]
                if lines:
                    post_title = lines
                    if len(post_title) > 70:
                        post_title = post_title[:67] + "..."

        if post_text or post_title != "Без заголовка":
            parsed_posts.append(
                {
                    "Дата публикации": post_date,
                    "Заголовок": post_title,
                    "Текст поста": post_text,
                }
            )
    return parsed_posts


async def scrape_single_group(semaphore, browser, item, results_dict):
    """Воркер, отвечающий за сбор данных с одной конкретной группы"""
    async with semaphore:  # Контролируем лимит одновременных потоков
        print(f"🛫 Запуск потока для: {item['name']}")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # Устанавливаем агрессивный таймаут в 25 секунд, чтобы скрипт не зависал на битых ссылках
            await page.goto(
                item["url"], wait_until="domcontentloaded", timeout=25000
            )

            # Умное быстрое ожидание появления первого блока новостей
            await page.wait_for_selector("div.feed", timeout=5000)

            # Вместо долгих пауз делаем 2 быстрых скролла для подгрузки базы
            for _ in range(2):
                await page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                await page.wait_for_timeout(
                    1200
                )  # Время сокращено до минимума для прогрузки пакетов

            # Хватаем отрендеренную страницу в память
            html_source = await page.content()

            # Парсим
            posts_data = parse_posts_from_html(html_source)

            if posts_data:
                results_dict[item["name"]] = posts_data
                print(
                    f"   🟢 [{item['name']}] успешно обработан. Собрано постов: {len(posts_data)}"
                )
            else:
                print(f"   🟡 [{item['name']}] открылся, но текстовых постов нет.")

        except Exception as e:
            print(f"   🔴 Ошибка при обработке {item['name']}: {e}")
        finally:
            await context.close()


async def main():
    print("⚡ Инициализация сверхбыстрого асинхронного парсера...")

    if not os.path.exists(INPUT_EXCEL_PATH):
        print(f"❌ Исходный Excel-файл не найден: {INPUT_EXCEL_PATH}")
        return

    targets = read_links_from_excel(INPUT_EXCEL_PATH)
    if not targets:
        print("⚠ В таблице нет подходящих ссылок на ОК.")
        return

    print(f"📖 Загружено задач из Excel: {len(targets)}")

    raw_results = []
    semaphore = asyncio.Semaphore(CONCURRENT_LIMITERS)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [
            scrape_single_group(semaphore, browser, item, raw_results)
            for item in targets
        ]
        await asyncio.gather(*tasks)
        await browser.close()

    # Формируем итоговый объект-словарь под требования структуры вашего метода
    job_payload = {
        "query": "Мониторинг публикаций Одноклассники",
        "days": 7,
        "keywords": ["ОК", "Парсинг", "Автоматизация"],
        "count": len(raw_results),
        "excluded_undated_count": sum(
            1 for x in raw_results if x["published_at"] is None
        ),
        "ai_mode": "off",
        "ai_error": None,
        "status": "success",
        "job_id": "job_ok_parser_v2",
        "results": raw_results,
    }

    # Вызов импортированной функции, генерирующей BytesIO
    print("\n📦 Передача данных в build_workbook...")
    excel_stream = build_workbook(job_payload)

    # Сохраняем BytesIO на жесткий диск для физической проверки результатов
    # ssdgseg

if __name__ == "__main__":
    asyncio.run(main())