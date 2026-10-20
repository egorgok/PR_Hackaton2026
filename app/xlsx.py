from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


def build_workbook(job: dict) -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Публикации"
    sheet.append(
        [
            "№",
            "Редакция",
            "Площадка",
            "Источник",
            "Заголовок",
            "Дата публикации",
            "Статус даты",
            "Ссылка",
            "Выдержка",
            "Связь с запросом",
            "Способ отбора",
            "Уверенность ИИ",
            "Причина проверки",
            "Совпавшие понятия",
        ]
    )
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="245C4F")

    for number, result in enumerate(job["results"], 1):
        row = sheet.max_row + 1
        sheet.append(
            [
                number,
                result["editor"],
                result["platform"],
                result["source_name"],
                result["title"],
                result["published_at"] or "Неизвестна",
                result["date_status"],
                result["url"],
                result["excerpt"],
                result["relevance"],
                result["match_method"],
                result.get("relevance_score"),
                result.get("relevance_reason"),
                ", ".join(result.get("matched_concepts", [])),
            ]
        )
        sheet.cell(row, 8).hyperlink = result["url"]
        sheet.cell(row, 8).style = "Hyperlink"
    widths = [8, 26, 16, 24, 48, 22, 18, 56, 72, 28, 20, 16, 60, 36]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    meta = workbook.create_sheet("Параметры поиска")
    meta.append(["Параметр", "Значение"])
    meta.append(["Запрос", job["query"]])
    meta.append(["Период, дней", job["days"]])
    meta.append(["Ключевые слова", ", ".join(job["keywords"])])
    meta.append(["Количество публикаций", job["count"]])
    meta.append(["Исключено: неизвестная дата", job.get("excluded_undated_count", 0)])
    meta.append(["Режим ИИ", job.get("ai_mode", "unknown")])
    meta.append(["Ошибка ИИ", job.get("ai_error") or "нет"])
    meta.append(["Статус", job["status"]])
    meta.append(["Задание", job["job_id"]])
    meta.column_dimensions["A"].width = 28
    meta.column_dimensions["B"].width = 100

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
