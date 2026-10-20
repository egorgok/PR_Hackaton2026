import os
import json
import requests
from datetime import datetime

VK_TOKEN = os.getenv("VK_TOKEN")          # токен не хранить в коде
VK_API_VERSION = "5.199"
COUNT = 100

def vk_api(method, params):
    params.update({
        "access_token": VK_TOKEN,
        "v": VK_API_VERSION,
    })

    response = requests.get(
        f"https://api.vk.com/method/{method}",
        params=params,
        timeout=20
    )
    data = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data["response"]


def get_id(group_id: str):
    result = vk_api("groups.getById", {
        "group_id": group_id
    })

    group_id = result["groups"][0]["id"]
    return -group_id


def parse_news(owner_id: int):
    result = vk_api("wall.get", {
        "owner_id": owner_id,
        "count": COUNT,
        "filter": "owner",
        "extended": 0,
    })

    news = []

    for post in result["items"]:
        print(post)
        news.append({
            "date": datetime.fromtimestamp(post["date"]).isoformat(),
            "text": post.get("text", "").strip(),
            "url": f"https://vk.com/wall{owner_id}_{post['id']}",
        })

    return news

def get_attachment_url(attachment):
    obj = attachment.get(attachment.get("type"), {})

    if attachment.get("type") == "photo":
        sizes = obj.get("sizes", [])
        return sizes[-1]["url"] if sizes else None

    if attachment.get("type") == "video":
        return f"https://vk.com/video{obj.get('owner_id')}_{obj.get('id')}"

    if attachment.get("type") == "link":
        return obj.get("url")

    return None

if name == "__main__":
    if not VK_TOKEN:
        raise RuntimeError("Укажите переменную окружения VK_TOKEN")

    news = parse_news("tubinka") # в скобках указываем груп айди.
    # пример:
    # vk.com/tubinka -> tubinka       | 
    # vk.com/priangarka -> priangarka | эт в арги указываем и он айдишник сам из этого возьмет
    # редакция, ВК, заголовок, текст, дата, юрл
    # print(f"Сохранено новостей: {len(news)}, {news}")