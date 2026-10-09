import io
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference, ScatterChart, Series
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import to_excel
from openpyxl.worksheet.worksheet import Worksheet

from app import models
from app.text import strip_control_chars

# Couleurs du burndown de l'app (--ink et --ink-muted, thème clair).
BURNDOWN_ACTUAL_COLOR = "0B0B0B"
BURNDOWN_IDEAL_COLOR = "898781"

ENTRY_HEADERS = ["Date", "Durée (h)", "Description", "Sprint", "Issue", "Catégorie"]

def _safe_cell(value):
    # Filet de sécurité : textes venant d'avant le nettoyage à la saisie, ou de
    # GitHub (titres d'issues). Un caractère de contrôle ferait échouer l'export.
    return strip_control_chars(value) if isinstance(value, str) else value


def _save(wb: Workbook) -> io.BytesIO:
    """Enregistre le classeur en neutralisant toute formule.

    Injection de formule : openpyxl transforme en formule toute chaîne qui
    commence par "=" — une description de saisie comme "=HYPERLINK(...)" ou
    "=cmd|..." serait évaluée à l'ouverture. Les données exportées sont des
    saisies d'utilisateurs (non fiables) et l'export ne contient aucune formule
    légitime : chaque cellule "formule" est donc forcée en texte, affiché tel
    quel (sans apostrophe ajoutée). Les autres préfixes (+, -, @) restent du
    texte dans un .xlsx et ne sont jamais évalués.
    """
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "f":
                    cell.data_type = "s"
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _safe_row(row: list) -> list:
    return [_safe_cell(value) for value in row]


def _entry_row(entry: models.TimeEntry) -> list:
    return _safe_row(
        [
            entry.date,
            entry.duration_hours,
            entry.description,
            entry.sprint.name if entry.sprint else "",
            f"#{entry.github_issue.number} {entry.github_issue.title}" if entry.github_issue else "",
            entry.category.name if entry.category else "",
        ]
    )


def _write_entries_sheet(ws: Worksheet, entries: list[models.TimeEntry], *, include_account: bool) -> None:
    headers = list(ENTRY_HEADERS)
    if include_account:
        headers.insert(1, "Compte")
    ws.append(headers)

    for entry in entries:
        row = _entry_row(entry)
        if include_account:
            row.insert(1, _safe_cell(entry.account_email))
        ws.append(row)

    for col_idx, header in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(14, len(header) + 4)


def _write_summary_table(
    ws: Worksheet, start_col: int, start_row: int, data: list[tuple[str, float]], *, label_header: str = "Libellé"
) -> None:
    """Écrit un petit tableau libellé/heures à partir de (start_row, start_col)."""
    ws.cell(row=start_row, column=start_col, value=label_header)
    ws.cell(row=start_row, column=start_col + 1, value="Heures")
    for offset, (label, hours) in enumerate(data, start=1):
        ws.cell(row=start_row + offset, column=start_col, value=_safe_cell(label))
        ws.cell(row=start_row + offset, column=start_col + 1, value=round(hours, 2))
    ws.column_dimensions[get_column_letter(start_col)].width = 22
    ws.column_dimensions[get_column_letter(start_col + 1)].width = 12


def _bar_chart(title: str, ws: Worksheet, start_col: int, start_row: int, count: int) -> BarChart:
    chart = BarChart()
    chart.title = title
    chart.y_axis.title = "Heures"
    data_ref = Reference(ws, min_col=start_col + 1, min_row=start_row, max_row=start_row + count)
    cats_ref = Reference(ws, min_col=start_col, min_row=start_row + 1, max_row=start_row + count)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    return chart


def _pie_chart(title: str, ws: Worksheet, start_col: int, start_row: int, count: int) -> PieChart:
    chart = PieChart()
    chart.title = title
    data_ref = Reference(ws, min_col=start_col + 1, min_row=start_row, max_row=start_row + count)
    cats_ref = Reference(ws, min_col=start_col, min_row=start_row + 1, max_row=start_row + count)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showPercent = True
    return chart


def _add_bar_chart_sheet(wb: Workbook, title: str, data: list[tuple[str, float]]) -> None:
    ws = wb.create_sheet(title[:31])
    _write_summary_table(ws, 1, 1, data)
    ws.add_chart(_bar_chart(title, ws, 1, 1, len(data)), "D2")


def _add_line_chart_sheet(wb: Workbook, title: str, data: list[tuple[str, float]]) -> None:
    ws = wb.create_sheet(title[:31])
    ws.append(["Date", "Heures"])
    for label, hours in data:
        ws.append([_safe_cell(label), round(hours, 2)])

    chart = LineChart()
    chart.title = title
    chart.y_axis.title = "Heures"
    data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(data) + 1)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(data) + 1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "D2")


def build_account_export(
    project: models.Project, account: models.Account, entries: list[models.TimeEntry]
) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Entrées"
    _write_entries_sheet(ws, entries, include_account=False)

    total_hours = sum(entry.duration_hours for entry in entries)
    ws.append([])
    ws.append(["Total", round(total_hours, 2)])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)

    if entries:
        hours_by_category: dict[str, float] = defaultdict(float)
        hours_by_sprint: dict[str, float] = defaultdict(float)
        for entry in entries:
            hours_by_category[entry.category.name if entry.category else "Sans catégorie"] += entry.duration_hours
            hours_by_sprint[entry.sprint.name if entry.sprint else "Sans sprint"] += entry.duration_hours

        category_data = sorted(hours_by_category.items(), key=lambda item: -item[1])
        sprint_data = sorted(hours_by_sprint.items(), key=lambda item: -item[1])

        # Tableaux récapitulatifs et graphiques sur la même feuille que les entrées
        # (colonnes H et au-delà), plutôt que sur des onglets séparés — tout doit
        # être visible d'un coup d'œil.
        CATEGORY_COL, SPRINT_COL, SUMMARY_ROW = 8, 11, 1  # H, K
        _write_summary_table(ws, CATEGORY_COL, SUMMARY_ROW, category_data)
        _write_summary_table(ws, SPRINT_COL, SUMMARY_ROW, sprint_data)

        ws.add_chart(_bar_chart("Par catégorie", ws, CATEGORY_COL, SUMMARY_ROW, len(category_data)), "N2")
        ws.add_chart(
            _pie_chart("Répartition par catégorie (%)", ws, CATEGORY_COL, SUMMARY_ROW, len(category_data)), "N18"
        )
        ws.add_chart(_bar_chart("Par sprint", ws, SPRINT_COL, SUMMARY_ROW, len(sprint_data)), "N34")

    return _save(wb)


def _burndown_series(ws: Worksheet, title: str, y_col: int, first_row: int, last_row: int) -> Series:
    x_values = Reference(ws, min_col=1, min_row=first_row, max_row=last_row)
    y_values = Reference(ws, min_col=y_col, min_row=first_row, max_row=last_row)
    series = Series(y_values, x_values, title=title)
    series.smooth = False
    return series


def build_burndown_export(sprint: models.Sprint, data: dict) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Burndown"

    ws.append(["Sprint", _safe_cell(sprint.name)])
    ws.append(["Début", sprint.start_date])
    ws.append(["Fin", sprint.end_date])
    ws.append(["Total story points", data["total_points"]])
    ws.append(["US sans valorisation", data["unestimated_issue_count"]])
    ws["B2"].number_format = ws["B3"].number_format = "dd/mm/yyyy"
    ws.append([])

    total_points = data["total_points"]
    total_days = (sprint.end_date - sprint.start_date).days or 1
    actual_by_date = {point["date"]: point["remaining_points"] for point in data["actual"]}
    # Le réel s'arrête à aujourd'hui (ou à la fin du sprint), comme dans l'app :
    # au-delà, la cellule reste vide et la courbe n'est pas prolongée.
    actual_end = max(actual_by_date, default=sprint.start_date)
    all_dates = sorted({point["date"] for point in data["ideal"]} | set(actual_by_date))

    ws.append(["Date", "Idéal (SP restants)", "Réel (SP restants)"])
    first_data_row = ws.max_row + 1
    last_actual = total_points
    for d in all_dates:
        fraction = max(0.0, min(1.0, (d - sprint.start_date).days / total_days))
        ideal_value = round(total_points * (1 - fraction), 2)
        if d in actual_by_date:
            last_actual = actual_by_date[d]
        ws.append([d, ideal_value, round(last_actual, 2) if d <= actual_end else None])
        ws.cell(row=ws.max_row, column=1).number_format = "dd/mm/yyyy"
    last_data_row = ws.max_row

    # Nuage de points relié par des segments droits : l'axe X est un vrai axe
    # de dates (les écarts entre fermetures d'US sont respectés), comme le
    # graphique de l'app — un LineChart les espacerait régulièrement et
    # lisserait les courbes.
    chart = ScatterChart()
    chart.title = f"Burndown — {_safe_cell(sprint.name)}"
    chart.style = 13
    chart.height = 9
    chart.width = 18
    chart.legend.position = "b"

    actual = _burndown_series(ws, "Réel", 3, first_data_row, last_data_row)
    actual.graphicalProperties.line.solidFill = BURNDOWN_ACTUAL_COLOR
    actual.graphicalProperties.line.width = 28575  # 2,25 pt
    actual.marker.symbol = "circle"
    actual.marker.size = 6
    actual.marker.graphicalProperties.solidFill = BURNDOWN_ACTUAL_COLOR
    actual.marker.graphicalProperties.line.solidFill = "FFFFFF"

    ideal = _burndown_series(ws, "Idéal", 2, first_data_row, last_data_row)
    ideal.graphicalProperties.line.solidFill = BURNDOWN_IDEAL_COLOR
    ideal.graphicalProperties.line.width = 19050  # 1,5 pt
    ideal.graphicalProperties.line.dashStyle = "dash"
    ideal.marker.symbol = "none"

    chart.series.extend([actual, ideal])

    chart.x_axis.title = "Date"
    chart.x_axis.number_format = "dd/mm"
    chart.x_axis.scaling.min = to_excel(sprint.start_date)
    chart.x_axis.scaling.max = to_excel(sprint.end_date)
    if total_days <= 31:
        chart.x_axis.majorUnit = 1 if total_days <= 14 else 7
    chart.x_axis.majorGridlines = None
    chart.y_axis.title = "Story points restants"
    chart.y_axis.scaling.min = 0
    chart.y_axis.number_format = "0"
    # openpyxl >= 3.1 masque les axes par défaut : sans ça, Excel n'affiche ni
    # dates ni graduations.
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    ws.add_chart(chart, "E2")

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20

    return _save(wb)


def build_project_export(
    project: models.Project, entries: list[models.TimeEntry], contributors: list[models.Account]
) -> io.BytesIO:
    wb = Workbook()
    ws_summary = wb.active
    ws_summary.title = "Synthèse"

    total_hours = sum(entry.duration_hours for entry in entries)
    contributor_count = len(contributors)
    average = round(total_hours / contributor_count, 2) if contributor_count else 0.0

    ws_summary.append(["Indicateur", "Valeur"])
    ws_summary.append(["Projet", _safe_cell(project.name)])
    ws_summary.append(["Total heures", round(total_hours, 2)])
    ws_summary.append(["Nombre de contributeurs", contributor_count])
    ws_summary.append(["Nombre d'entrées", len(entries)])
    ws_summary.append(["Moyenne heures / contributeur", average])
    ws_summary.column_dimensions["A"].width = 24
    ws_summary.column_dimensions["B"].width = 30

    ws_entries = wb.create_sheet("Entrées")
    _write_entries_sheet(ws_entries, entries, include_account=True)

    hours_by_account: dict[str, float] = defaultdict(float)
    hours_by_sprint: dict[str, float] = defaultdict(float)
    hours_by_date: dict[str, float] = defaultdict(float)
    for entry in entries:
        hours_by_account[entry.account_email] += entry.duration_hours
        hours_by_sprint[entry.sprint.name if entry.sprint else "Sans sprint"] += entry.duration_hours
        hours_by_date[entry.date.isoformat()] += entry.duration_hours

    if entries:
        _add_bar_chart_sheet(wb, "Heures par membre", sorted(hours_by_account.items(), key=lambda item: -item[1]))
        _add_bar_chart_sheet(
            wb, "Répartition par sprint", sorted(hours_by_sprint.items(), key=lambda item: -item[1])
        )
        _add_line_chart_sheet(wb, "Évolution temporelle", sorted(hours_by_date.items()))

    return _save(wb)
