"""Images insérées dans les comptes-rendus Word, dessinées avec Pillow.

On dessine en double résolution puis on réduit (anti-crénelage) : Pillow ne
lisse pas les cercles et les traits épais.
"""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE = 2

# Liberation Sans (SIL OFL 1.1, métriques identiques à Arial) est livrée avec
# l'application : l'image Docker n'a aucune police système, et la police
# embarquée par Pillow n'a pas les accents ("Qualité").
_FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "LiberationSans-Regular.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FONT_PATH), size * SCALE)


def _finish(image: Image.Image) -> BytesIO:
    width, height = image.size
    image = image.resize((width // SCALE, height // SCALE), Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# Centres et rayon des trois cercles (coordonnées en 1x).
_TIME = (400, 330)
_QUALITY = (600, 330)
_SCOPE = (500, 500)
_RADIUS = 160

# Position du point rouge pour chaque valeur de `balance` : chaque point est
# choisi pour tomber dans la seule zone du diagramme qu'il représente.
BALANCE_POINTS = {
    "all": (500, 387),
    "time_quality": (500, 270),
    "time_scope": (407, 440),
    "quality_scope": (593, 440),
    "time": (320, 290),
    "quality": (680, 290),
    "scope": (500, 590),
}


def project_balance_diagram(balance: str, point: tuple[float, float] | None = None) -> BytesIO:
    """Diagramme de Venn Temps / Qualité / Respect du cahier des charges, avec
    un point rouge indiquant où se situe le projet : à `point` s'il a été placé
    librement, sinon au centre de la zone prédéfinie `balance`."""
    s = SCALE
    image = Image.new("RGB", (1000 * s, 820 * s), "white")
    draw = ImageDraw.Draw(image)

    for cx, cy in (_TIME, _QUALITY, _SCOPE):
        draw.ellipse(
            ((cx - _RADIUS) * s, (cy - _RADIUS) * s, (cx + _RADIUS) * s, (cy + _RADIUS) * s),
            outline="#333333",
            width=2 * s,
        )

    font = _font(44)
    draw.text((150 * s, 180 * s), "Temps", fill="#222222", font=font, anchor="mm")
    draw.text((850 * s, 180 * s), "Qualité", fill="#222222", font=font, anchor="mm")
    draw.multiline_text(
        (500 * s, 740 * s),
        "Respect du cahier des\ncharges",
        fill="#222222",
        font=font,
        anchor="mm",
        align="center",
        spacing=8 * s,
    )

    px, py = point if point is not None else BALANCE_POINTS.get(balance, BALANCE_POINTS["all"])
    dot = 14
    draw.ellipse(((px - dot) * s, (py - dot) * s, (px + dot) * s, (py + dot) * s), fill="#e00000", outline="#7a0000", width=s)
    return _finish(image)


def _daily_series(points: list[dict], start: date, end: date) -> list[tuple[date, float]]:
    """Transforme les points de rupture du burndown (début, fermetures, date
    butoir) en une valeur par jour : le restant à la fin de chaque journée."""
    ordered = sorted(points, key=lambda p: p["date"])
    series: list[tuple[date, float]] = []
    current = ordered[0]["remaining_points"] if ordered else 0.0
    index = 0
    day = start
    while day <= end:
        while index < len(ordered) and ordered[index]["date"] <= day:
            current = ordered[index]["remaining_points"]
            index += 1
        series.append((day, current))
        day += timedelta(days=1)
    return series


def burndown_chart(title: str, burndown: dict, start: date, end: date) -> BytesIO:
    """Courbe de burndown (réel en bleu, idéal en rouge), dans l'esprit du
    graphique Google Sheets des comptes-rendus existants."""
    s = SCALE
    width, height = 1600, 900
    left, right, top, bottom = 110, 60, 110, 170
    image = Image.new("RGB", (width * s, height * s), "white")
    draw = ImageDraw.Draw(image)

    actual = burndown["actual"]
    cutoff = max(p["date"] for p in actual) if actual else start
    series = _daily_series(actual, start, cutoff)
    total = float(burndown["total_points"] or 0)
    y_max = max([total] + [value for _, value in series]) or 1.0
    # Graduation "ronde" de l'axe Y, 4 à 5 intervalles.
    raw_step = y_max / 4
    magnitude = 10 ** max(len(str(int(raw_step))) - 1, 0)
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw_step)
    y_top = step * (int(y_max / step) + (0 if y_max % step == 0 else 1))

    plot_w = width - left - right
    plot_h = height - top - bottom
    days = max((end - start).days, 1)

    def x_of(day: date) -> float:
        return (left + plot_w * (day - start).days / days) * s

    def y_of(value: float) -> float:
        return (top + plot_h * (1 - value / y_top)) * s

    label_font = _font(22)
    draw.text((left * s, 45 * s), title, fill="#555555", font=_font(28), anchor="lm")

    value = 0.0
    while value <= y_top + 1e-9:
        y = y_of(value)
        draw.line((left * s, y, (width - right) * s, y), fill="#e3e3e3", width=s)
        text = f"{value:g}".replace(".", ",")
        draw.text(((left - 15) * s, y), text, fill="#555555", font=label_font, anchor="rm")
        value += step

    label_every = max(1, -(-(days + 1) // 12))
    day = start
    index = 0
    while day <= end:
        if index % label_every == 0 or day == end:
            draw.text((x_of(day), (height - bottom + 30) * s), day.strftime("%d/%m"), fill="#555555", font=label_font, anchor="mt")
        day += timedelta(days=1)
        index += 1

    draw.line((x_of(start), y_of(total), x_of(end), y_of(0)), fill="#e53935", width=3 * s)

    coords = [(x_of(d), y_of(v)) for d, v in series]
    if len(coords) > 1:
        draw.line(coords, fill="#4285f4", width=4 * s, joint="curve")
    for x, y in coords:
        r = 7 * s
        draw.ellipse((x - r, y - r, x + r, y + r), fill="#4285f4")

    legend_y = (height - 55) * s
    cx = width / 2
    draw.ellipse(((cx - 150) * s - 9 * s, legend_y - 9 * s, (cx - 150) * s + 9 * s, legend_y + 9 * s), fill="#4285f4")
    draw.text(((cx - 130) * s, legend_y), "Réel", fill="#333333", font=label_font, anchor="lm")
    draw.line(((cx + 10) * s, legend_y, (cx + 50) * s, legend_y), fill="#e53935", width=3 * s)
    draw.text(((cx + 60) * s, legend_y), "Idéal", fill="#333333", font=label_font, anchor="lm")
    return _finish(image)
