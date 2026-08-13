import io
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app import models

ENTRY_HEADERS = ["Date", "Durée (h)", "Description", "Sprint", "Issue", "Catégorie"]


def _entry_row(entry: models.TimeEntry) -> list:
    return [
        entry.date,
        entry.duration_hours,
        entry.description,
        entry.sprint.name if entry.sprint else "",
        f"#{entry.github_issue.number} {entry.github_issue.title}" if entry.github_issue else "",
        entry.category.name if entry.category else "",
    ]


def _write_entries_sheet(ws: Worksheet, entries: list[models.TimeEntry], *, include_member: bool) -> None:
    headers = list(ENTRY_HEADERS)
    if include_member:
        headers.insert(1, "Membre")
    ws.append(headers)

    for entry in entries:
        row = _entry_row(entry)
        if include_member:
            row.insert(1, entry.member_name)
        ws.append(row)

    for col_idx, header in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(14, len(header) + 4)


def _add_bar_chart_sheet(wb: Workbook, title: str, data: list[tuple[str, float]]) -> None:
    ws = wb.create_sheet(title[:31])
    ws.append(["Libellé", "Heures"])
    for label, hours in data:
        ws.append([label, round(hours, 2)])

    chart = BarChart()
    chart.title = title
    chart.y_axis.title = "Heures"
    data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(data) + 1)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(data) + 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "D2")


def _add_line_chart_sheet(wb: Workbook, title: str, data: list[tuple[str, float]]) -> None:
    ws = wb.create_sheet(title[:31])
    ws.append(["Date", "Heures"])
    for label, hours in data:
        ws.append([label, round(hours, 2)])

    chart = LineChart()
    chart.title = title
    chart.y_axis.title = "Heures"
    data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(data) + 1)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(data) + 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "D2")


def build_member_export(
    project: models.Project, member: models.Member, entries: list[models.TimeEntry]
) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Entrées"
    _write_entries_sheet(ws, entries, include_member=False)

    hours_by_category: dict[str, float] = defaultdict(float)
    hours_by_sprint: dict[str, float] = defaultdict(float)
    for entry in entries:
        hours_by_category[entry.category.name if entry.category else "Sans catégorie"] += entry.duration_hours
        hours_by_sprint[entry.sprint.name if entry.sprint else "Sans sprint"] += entry.duration_hours

    if entries:
        _add_bar_chart_sheet(wb, "Par catégorie", sorted(hours_by_category.items(), key=lambda item: -item[1]))
        _add_bar_chart_sheet(wb, "Par sprint", sorted(hours_by_sprint.items(), key=lambda item: -item[1]))

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def build_project_export(
    project: models.Project, entries: list[models.TimeEntry], members: list[models.Member]
) -> io.BytesIO:
    wb = Workbook()
    ws_summary = wb.active
    ws_summary.title = "Synthèse"

    total_hours = sum(entry.duration_hours for entry in entries)
    member_count = len(members)
    average = round(total_hours / member_count, 2) if member_count else 0.0

    ws_summary.append(["Indicateur", "Valeur"])
    ws_summary.append(["Projet", project.name])
    ws_summary.append(["Total heures", round(total_hours, 2)])
    ws_summary.append(["Nombre de membres", member_count])
    ws_summary.append(["Nombre d'entrées", len(entries)])
    ws_summary.append(["Moyenne heures / membre", average])
    ws_summary.column_dimensions["A"].width = 24
    ws_summary.column_dimensions["B"].width = 30

    ws_entries = wb.create_sheet("Entrées")
    _write_entries_sheet(ws_entries, entries, include_member=True)

    hours_by_member: dict[str, float] = defaultdict(float)
    hours_by_sprint: dict[str, float] = defaultdict(float)
    hours_by_date: dict[str, float] = defaultdict(float)
    for entry in entries:
        hours_by_member[entry.member_name] += entry.duration_hours
        hours_by_sprint[entry.sprint.name if entry.sprint else "Sans sprint"] += entry.duration_hours
        hours_by_date[entry.date.isoformat()] += entry.duration_hours

    if entries:
        _add_bar_chart_sheet(wb, "Heures par membre", sorted(hours_by_member.items(), key=lambda item: -item[1]))
        _add_bar_chart_sheet(
            wb, "Répartition par sprint", sorted(hours_by_sprint.items(), key=lambda item: -item[1])
        )
        _add_line_chart_sheet(wb, "Évolution temporelle", sorted(hours_by_date.items()))

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
