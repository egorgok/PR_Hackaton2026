from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from openpyxl import load_workbook

from app.models import Platform


COLUMNS = {
    Platform.website: "Сайты",
    Platform.telegram: "ТГ",
    Platform.vk: "ВК",
    Platform.ok: "ОК",
    Platform.zen: "ДЗЕН",
    Platform.max: "МАХ",
}


@dataclass(frozen=True)
class Source:
    editor: str
    platform: Platform
    url: str

    @property
    def host(self) -> str:
        return urlparse(self.url).hostname or self.url


class SourceRegistry:
    def __init__(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Файл реестра источников не найден: {path}")
        self.path = path
        self._items = self._load(path)

    @staticmethod
    def _load(path: Path) -> list[Source]:
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook["Лист1"] if "Лист1" in workbook.sheetnames else workbook.active
        headers = {
            str(cell.value).strip(): index
            for index, cell in enumerate(sheet[1])
            if cell.value is not None
        }
        items: list[Source] = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            editor_value = row[headers.get("Редакция газеты", 0)]
            if not editor_value:
                continue
            editor = " ".join(str(editor_value).split())
            for platform, column in COLUMNS.items():
                index = headers.get(column)
                if index is None or index >= len(row) or not row[index]:
                    continue
                raw_url = str(row[index]).strip()
                if not raw_url.startswith(("https://", "http://")):
                    raw_url = "https://" + raw_url
                items.append(Source(editor, platform, raw_url))
        workbook.close()
        return items

    def list_sources(self) -> list[dict[str, str]]:
        return [
            {"editor": item.editor, "platform": item.platform.value, "url": item.url}
            for item in self._items
        ]

    def all_sources(self, platforms: list[Platform]) -> list[Source]:
        selected_platforms = set(platforms)
        return [
            item
            for item in self._items
            if item.platform in selected_platforms
        ]

    def resolve_selection(
        self, platforms: list[Platform], editors: list[str]
    ) -> list[Source | dict[str, str]]:
        selected: list[Source | dict[str, str]] = []
        seen: set[tuple[str, Platform]] = set()
        known_editors = {item.editor.casefold() for item in self._items}
        for editor_input in editors:
            editor = " ".join(editor_input.split())
            if editor.casefold() not in known_editors:
                for platform in platforms:
                    selected.append(
                        {
                            "editor": editor,
                            "platform": platform.value,
                            "url": "",
                            "message": "Редакция отсутствует в реестре источников.",
                        }
                    )
                continue
            for platform in platforms:
                key = (editor.casefold(), platform)
                if key in seen:
                    continue
                seen.add(key)
                source = next(
                    (
                        item
                        for item in self._items
                        if item.editor.casefold() == editor.casefold()
                        and item.platform == platform
                    ),
                    None,
                )
                if source is None:
                    selected.append(
                        {
                            "editor": editor,
                            "platform": platform.value,
                            "url": "",
                            "message": "Для редакции нет адреса на выбранной площадке.",
                        }
                    )
                else:
                    selected.append(source)
        return selected
