from __future__ import annotations

import argparse
import math
import textwrap
from collections import defaultdict
from pathlib import Path
import unicodedata

import pandas as pd

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except ModuleNotFoundError:
    plt = None
    PdfPages = None


ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_SABERES_CSV = OUTPUT_DIR / "personas_saberes.csv"
DEFAULT_CURSOS_CSV = OUTPUT_DIR / "personas_cursos.csv"
DEFAULT_PERSONAS_CSV = ROOT_DIR / "00_datos.csv"
DEFAULT_PLAN_CSV = BASE_DIR / "data" / "plan_de_estudios.csv"
DEFAULT_PDF = OUTPUT_DIR / "personas_saberes_graficos.pdf"
UNASSIGNED_COURSE_EXCEPTIONS = {"CYD0106", "AUT0205", "CYD0206"}
UNASSIGNED_COURSE_CODE_EXCEPTIONS = {"EE1103", "EE1104"}

AREA_COLORS = {
    "ADD": "#4E79A7",
    "AER": "#F28E2B",
    "AUT": "#59A14F",
    "CIB": "#E15759",
    "CYD": "#76B7B2",
    "FPH": "#EDC948",
    "IEE": "#B07AA1",
    "IMM": "#FF9DA7",
    "INS": "#9C755F",
    "SCF": "#BAB0AC",
    "MULTI": "#6B7280",
}


def area_key(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    if ";" in text:
        return "MULTI"
    return text.strip() or "MULTI"


def wrap_label(value: object, width: int = 48) -> str:
    text = "" if pd.isna(value) else str(value)
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path).fillna("")


def split_codes(value: object) -> list[str]:
    text = "" if pd.isna(value) else str(value)
    return [part.strip() for part in text.split(";") if part.strip()]


def unique_preserving_order(values: list[str]) -> list[str]:
    unique = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        unique.append(value)
        seen.add(value)
    return unique


def parse_float(value: object) -> float:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


def format_credit_score(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value)} cr"
    return f"{value:.1f} cr"


def format_course_meta(credits: float, semester: str) -> str:
    parts = []
    if credits > 0:
        credit_text = f"{int(credits)} Cr." if float(credits).is_integer() else f"{credits:.1f} Cr."
        parts.append(credit_text)
    if semester:
        parts.append(f"S{semester}")
    return " ".join(parts)


def ellipsize(value: str, max_chars: int) -> str:
    if max_chars <= 3 or len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.lower()
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def parse_saber_name(code: str, labels: list[str], index: int) -> str:
    if index >= len(labels):
        return code
    label = labels[index].strip()
    prefix = f"{code} - "
    if label.startswith(prefix):
        return label[len(prefix) :].strip()
    if " - " in label:
        label_code, label_name = label.split(" - ", 1)
        if label_code.strip() == code:
            return label_name.strip()
    return label or code


def expand_summary_saberes(saberes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in saberes.itertuples(index=False):
        row_data = row._asdict()
        codes = split_codes(row_data.get("saberes", ""))
        areas = split_codes(row_data.get("area", ""))
        labels = split_codes(row_data.get("saberes_nombres", ""))
        for index, code in enumerate(codes):
            cod_area = areas[index] if index < len(areas) else ""
            rows.append(
                {
                    "codigo": row_data.get("codigo", ""),
                    "persona": row_data.get("persona", ""),
                    "codArea": cod_area,
                    "area": cod_area,
                    "codSaber": code,
                    "saber": parse_saber_name(code, labels, index),
                    "score": 1.0,
                }
            )
    return pd.DataFrame(rows)


def normalize_saberes_input(saberes: pd.DataFrame, saberes_path: Path) -> pd.DataFrame:
    detailed_columns = {"codigo", "persona", "codArea", "codSaber", "saber", "score"}
    if detailed_columns <= set(saberes.columns):
        return saberes

    summary_columns = {"codigo", "persona", "saberes", "area", "saberes_nombres"}
    if summary_columns <= set(saberes.columns):
        return expand_summary_saberes(saberes)

    missing_detailed = sorted(detailed_columns - set(saberes.columns))
    missing_summary = sorted(summary_columns - set(saberes.columns))
    raise ValueError(
        f"Missing columns in {saberes_path}. "
        f"Detailed format missing: {missing_detailed}; "
        f"summary format missing: {missing_summary}"
    )


def build_saber_credit_scores(cursos_path: Path) -> dict[str, dict[str, float]]:
    if not cursos_path.exists():
        return {}
    cursos = read_csv(cursos_path)
    required_columns = {"codigo_persona", "saberes_requeridos", "creditos"}
    if not required_columns <= set(cursos.columns):
        return {}

    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in cursos.itertuples(index=False):
        row_data = row._asdict()
        codigo = str(row_data.get("codigo_persona", "")).strip()
        if not codigo:
            continue
        credits = parse_float(row_data.get("creditos", 0))
        saberes_requeridos = unique_preserving_order(
            split_codes(row_data.get("saberes_requeridos", ""))
        )
        for code in saberes_requeridos:
            scores[codigo][code] += credits
    return {codigo: dict(values) for codigo, values in scores.items()}


def apply_course_credit_scores(saberes: pd.DataFrame, cursos_path: Path) -> pd.DataFrame:
    credit_scores = build_saber_credit_scores(cursos_path)
    if not credit_scores:
        return saberes

    scored = saberes.copy()
    scored["score"] = [
        credit_scores.get(str(row.codigo), {}).get(str(row.codSaber), 0.0)
        for row in scored.itertuples(index=False)
    ]
    return scored


def build_person_list(personas_path: Path, saberes: pd.DataFrame) -> pd.DataFrame:
    personas = saberes[["codigo", "persona"]].drop_duplicates().copy()
    if personas_path.exists():
        names = read_csv(personas_path)[["codigo", "nombre"]].rename(
            columns={"nombre": "persona_datos"}
        )
        personas = personas.merge(names, on="codigo", how="left")
        personas["persona"] = personas["persona"].where(
            personas["persona"].astype(str).str.strip() != "",
            personas["persona_datos"],
        )
        personas = personas.drop(columns=["persona_datos"])
    return personas.sort_values("persona")


def build_course_counts(cursos_path: Path) -> dict[str, int]:
    if not cursos_path.exists():
        return {}
    cursos = read_csv(cursos_path)
    if "codigo_persona" not in cursos.columns:
        return {}
    return cursos.groupby("codigo_persona").size().to_dict()


def build_courses_by_person(cursos_path: Path) -> dict[str, list[dict[str, object]]]:
    if not cursos_path.exists():
        return {}
    cursos = read_csv(cursos_path)
    if "codigo_persona" not in cursos.columns:
        return {}

    for column in ("semestre", "codigo_curso", "id_curso", "curso"):
        if column not in cursos.columns:
            cursos[column] = ""
    cursos["_semestre_sort"] = pd.to_numeric(cursos["semestre"], errors="coerce").fillna(999)
    cursos = cursos.sort_values(["codigo_persona", "_semestre_sort", "codigo_curso", "id_curso", "curso"])

    courses_by_person: dict[str, list[dict[str, object]]] = {}
    for codigo, group in cursos.groupby("codigo_persona", sort=False):
        courses_by_person[str(codigo)] = [
            {
                "semestre": row.semestre,
                "codigo_curso": row.codigo_curso,
                "id_curso": row.id_curso,
                "curso": row.curso,
                "creditos": row.creditos if "creditos" in group.columns else "",
            }
            for row in group.itertuples(index=False)
        ]
    return courses_by_person


def format_course_label(course: dict[str, object]) -> str:
    semester = str(course.get("semestre", "")).strip()
    course_code = str(course.get("codigo_curso", "")).strip()
    course_id = str(course.get("id_curso", "")).strip()
    course_name = str(course.get("curso", "")).strip()
    credits = parse_float(course.get("creditos", ""))

    label = course_code or course_id
    if course_name:
        label = f"{label} - {course_name}" if label else course_name

    meta = format_course_meta(credits, semester)
    if meta:
        label = f"{label} ({meta})"
    return label


def format_plan_course_label(course: dict[str, object]) -> str:
    semester = str(course.get("semestre", "")).strip()
    course_code = str(course.get("codigo", "")).strip()
    course_id = str(course.get("id", "")).strip()
    course_name = str(course.get("nombre", "")).strip()
    credits = parse_float(course.get("creditos", ""))

    label = course_code or course_id
    if course_name:
        label = f"{label} - {course_name}" if label else course_name

    meta = format_course_meta(credits, semester)
    if meta:
        label = f"{label} ({meta})"
    return label


def include_unassigned_course(row: dict[str, object]) -> bool:
    course_id = str(row.get("id", "")).strip()
    course_code = str(row.get("codigo", "")).strip()
    area = course_id[:3]
    name = normalize_text(row.get("nombre", ""))

    if course_id in UNASSIGNED_COURSE_EXCEPTIONS:
        return False
    if course_code in UNASSIGNED_COURSE_CODE_EXCEPTIONS:
        return False
    if area == "CIB":
        return False
    if area == "CYD" and "ingles" in name:
        return False
    if area == "FPH":
        is_project_admin = "administracion" in name and "proyecto" in name
        is_intro_eiem = "introduccion" in name and "ingenieria electromecanica" in name
        return is_project_admin or is_intro_eiem
    return True


def build_unassigned_courses(plan_path: Path, cursos_path: Path) -> list[dict[str, object]]:
    plan = read_csv(plan_path)
    required_columns = {"id", "semestre", "codigo", "nombre", "creditos"}
    missing = required_columns - set(plan.columns)
    if missing:
        raise ValueError(f"Missing columns in {plan_path}: {sorted(missing)}")

    assigned_ids: set[str] = set()
    assigned_codes: set[str] = set()
    if cursos_path.exists():
        cursos = read_csv(cursos_path)
        if "id_curso" in cursos.columns:
            assigned_ids = {
                str(course_id).strip()
                for course_id in cursos["id_curso"]
                if str(course_id).strip()
            }
        if "codigo_curso" in cursos.columns:
            assigned_codes = {
                str(course_code).strip()
                for course_code in cursos["codigo_curso"]
                if str(course_code).strip()
            }

    plan_ids = plan["id"].astype(str).str.strip()
    plan_codes = plan["codigo"].astype(str).str.strip()
    unassigned = plan[
        ~plan_ids.isin(assigned_ids)
        & (~plan_codes.isin(assigned_codes) | (plan_codes == ""))
    ].copy()
    unassigned["_semestre_sort"] = pd.to_numeric(unassigned["semestre"], errors="coerce").fillna(999)
    unassigned = unassigned.sort_values(["_semestre_sort", "id", "codigo", "nombre"])

    rows: list[dict[str, object]] = []
    seen_course_keys: set[str] = set()
    for row in unassigned.itertuples(index=False):
        row_data = row._asdict()
        if not include_unassigned_course(row_data):
            continue
        course_key = str(row_data.get("codigo", "")).strip() or str(row_data.get("id", "")).strip()
        if course_key in seen_course_keys:
            continue
        rows.append(row_data)
        seen_course_keys.add(course_key)
    return rows


def course_label_columns(
    courses: list[dict[str, object]],
    max_columns: int = 2,
    max_rows: int = 9,
) -> list[list[str]]:
    labels = [format_course_label(course) for course in courses]
    if not labels:
        return []

    column_count = 1 if len(labels) <= max_rows else max_columns
    max_items = column_count * max_rows
    if len(labels) > max_items:
        visible_count = max_items - 1
        hidden_count = len(labels) - visible_count
        labels = labels[:visible_count] + [f"... y {hidden_count} cursos mas"]

    rows_per_column = math.ceil(len(labels) / column_count)
    return [
        labels[index : index + rows_per_column]
        for index in range(0, len(labels), rows_per_column)
    ]


def plan_course_label_columns(
    courses: list[dict[str, object]],
    max_columns: int = 2,
    max_rows: int = 28,
) -> list[list[str]]:
    labels = [format_plan_course_label(course) for course in courses]
    if not labels:
        return []

    column_count = min(max_columns, max(1, math.ceil(len(labels) / max_rows)))
    max_items = column_count * max_rows
    if len(labels) > max_items:
        visible_count = max_items - 1
        hidden_count = len(labels) - visible_count
        labels = labels[:visible_count] + [f"... y {hidden_count} cursos mas"]

    rows_per_column = math.ceil(len(labels) / column_count)
    return [
        labels[index : index + rows_per_column]
        for index in range(0, len(labels), rows_per_column)
    ]


def add_courses_to_figure(
    fig,
    courses: list[dict[str, object]],
    x: float,
    title_y: float,
    max_chars: int,
) -> None:
    fig.text(x, title_y, "Cursos asignados", fontsize=8, fontweight="bold", color="#111111")
    max_rows = max(1, int((title_y - 0.06) / 0.017))
    columns = course_label_columns(courses, max_columns=1, max_rows=max_rows)
    if not columns:
        fig.text(x, title_y - 0.025, "Sin cursos asignados.", fontsize=7, color="#555555")
        return

    y = title_y - 0.025
    for label in columns[0]:
        fig.text(x, y, ellipsize(label, max_chars), fontsize=6.3, color="#333333")
        y -= 0.017


def plot_unassigned_courses_page(
    pdf: PdfPages,
    unassigned_courses: list[dict[str, object]],
) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.06, 0.92, "Cursos sin asignar", fontsize=18, fontweight="bold", color="#111111")

    if not unassigned_courses:
        fig.text(0.06, 0.78, "No hay cursos sin asignar con estos filtros.", fontsize=11, color="#333333")
    else:
        fig.text(0.06, 0.875, f"Total: {len(unassigned_courses)} cursos", fontsize=9, color="#333333")
        columns = plan_course_label_columns(unassigned_courses)
        x_positions = [0.06, 0.52]
        for column_index, labels in enumerate(columns):
            x = x_positions[column_index]
            y = 0.835
            for label in labels:
                fig.text(x, y, ellipsize(label, 92), fontsize=5.8, color="#333333")
                y -= 0.027

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def plot_empty_page(
    pdf: PdfPages,
    codigo: str,
    persona: str,
    courses: list[dict[str, object]],
) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.text(0.02, 0.92, persona, fontsize=18, fontweight="bold", transform=ax.transAxes)
    ax.text(0.02, 0.86, f"Codigo: {codigo}", fontsize=11, color="#555555", transform=ax.transAxes)
    ax.text(
        0.02,
        0.55,
        "No hay saberes clasificados para esta persona con los criterios actuales.",
        fontsize=13,
        color="#333333",
        transform=ax.transAxes,
    )
    add_courses_to_figure(fig, courses, x=0.06, title_y=0.30, max_chars=118)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def plot_person(
    pdf: PdfPages,
    codigo: str,
    persona: str,
    group: pd.DataFrame,
    course_count: int,
    courses: list[dict[str, object]],
    top_n: int | None,
) -> None:
    data = group.copy()
    data["score"] = pd.to_numeric(data["score"], errors="coerce").fillna(0)
    data = data[data["score"] > 0]
    if data.empty or float(data["score"].sum()) <= 0:
        plot_empty_page(pdf, codigo, persona, courses)
        return
    data = data.sort_values(["score", "codArea", "codSaber"], ascending=[False, True, True])
    if top_n is not None:
        data = data.head(top_n)
    data = data.sort_values("score", ascending=False)

    labels = [str(row.codSaber) for row in data.itertuples()]
    legend_labels = [wrap_label(f"{row.codSaber} - {row.saber}", width=42) for row in data.itertuples()]
    colors = [AREA_COLORS.get(area_key(row.codArea), "#6B7280") for row in data.itertuples()]

    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.subplots_adjust(left=0.05, right=0.68, top=0.86, bottom=0.08)
    wedges, _, autotexts = ax.pie(
        data["score"],
        labels=labels,
        colors=colors,
        startangle=90,
        counterclock=False,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
        pctdistance=0.72,
        labeldistance=1.06,
        wedgeprops={"linewidth": 0.7, "edgecolor": "white"},
        textprops={"fontsize": 9},
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(8)
        autotext.set_fontweight("bold")

    ax.axis("equal")
    ax.set_title(persona, loc="left", fontsize=16, fontweight="bold", pad=16)
    subtitle = f"Codigo: {codigo}   |   Saberes: {len(data)}   |   Cursos clasificados: {course_count}"
    ax.text(0, 1.01, subtitle, transform=ax.transAxes, fontsize=9, color="#555555")

    total_score = float(data["score"].sum())
    legend_with_scores = [
        f"{label}  ({format_credit_score(float(score))}, {score / total_score:.0%})"
        for label, score in zip(legend_labels, data["score"], strict=False)
    ]
    ax.legend(
        wedges,
        legend_with_scores,
        title="Saberes",
        loc="center left",
        bbox_to_anchor=(1.0, 0.74),
        frameon=False,
        fontsize=8,
        title_fontsize=9,
    )

    course_title_y = max(0.16, 0.72 - len(data) * 0.047)
    add_courses_to_figure(fig, courses, x=0.70, title_y=course_title_y, max_chars=64)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def draw_wrapped_text(
    page,
    text: str,
    x: float,
    y: float,
    width: int,
    font_name: str = "Helvetica",
    font_size: int = 8,
    leading: int = 10,
) -> float:
    page.setFont(font_name, font_size)
    lines = []
    for paragraph in str(text).split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=False) or [""])
    for line in lines:
        page.drawString(x, y, line)
        y -= leading
    return y


def reportlab_color(hex_color: str):
    from reportlab.lib import colors

    return colors.HexColor(hex_color)


def plot_empty_page_reportlab(page, codigo: str, persona: str, page_width: float, page_height: float) -> None:
    page.setFont("Helvetica-Bold", 18)
    page.drawString(36, page_height - 54, persona)
    page.setFont("Helvetica", 11)
    page.setFillColor(reportlab_color("#555555"))
    page.drawString(36, page_height - 78, f"Codigo: {codigo}")
    page.setFillColor(reportlab_color("#333333"))
    page.setFont("Helvetica", 13)
    page.drawString(
        36,
        page_height / 2,
        "No hay saberes clasificados para esta persona con los criterios actuales.",
    )


def draw_courses_reportlab(
    page,
    courses: list[dict[str, object]],
    x: float,
    width: float,
    title_y: float,
    bottom_y: float = 36,
) -> None:
    page.setFillColor(reportlab_color("#111111"))
    page.setFont("Helvetica-Bold", 8)
    page.drawString(x, title_y, "Cursos asignados")

    font_size = 6.2
    leading = 8.2
    max_rows = max(1, int((title_y - 13 - bottom_y) // leading))
    columns = course_label_columns(courses, max_columns=1, max_rows=max_rows)
    if not columns:
        page.setFillColor(reportlab_color("#555555"))
        page.setFont("Helvetica", 7)
        page.drawString(x, title_y - 13, "Sin cursos asignados.")
        return

    y = title_y - 13
    max_chars = max(24, int(width / (font_size * 0.50)))
    page.setFillColor(reportlab_color("#333333"))
    page.setFont("Helvetica", font_size)
    for label in columns[0]:
        page.drawString(x, y, ellipsize(label, max_chars))
        y -= leading


def draw_unassigned_courses_page_reportlab(
    page,
    unassigned_courses: list[dict[str, object]],
    page_width: float,
    page_height: float,
) -> None:
    left_margin = 36
    right_margin = 36
    top_y = page_height - 44

    page.setFillColor(reportlab_color("#111111"))
    page.setFont("Helvetica-Bold", 18)
    page.drawString(left_margin, top_y, "Cursos sin asignar")

    if not unassigned_courses:
        page.setFillColor(reportlab_color("#333333"))
        page.setFont("Helvetica", 11)
        page.drawString(
            left_margin,
            top_y - 76,
            "No hay cursos sin asignar con estos filtros.",
        )
        return

    page.setFillColor(reportlab_color("#333333"))
    page.setFont("Helvetica", 9)
    page.drawString(left_margin, top_y - 28, f"Total: {len(unassigned_courses)} cursos")

    columns = plan_course_label_columns(unassigned_courses)
    column_gap = 24
    column_count = len(columns)
    available_width = page_width - left_margin - right_margin
    column_width = (available_width - column_gap * (column_count - 1)) / column_count
    font_size = 5.8
    y_start = top_y - 58
    max_rows_in_column = max(len(labels) for labels in columns)
    leading = min(16, max(9, (y_start - 42) / max_rows_in_column))

    page.setFillColor(reportlab_color("#333333"))
    page.setFont("Helvetica", font_size)
    for column_index, labels in enumerate(columns):
        x = left_margin + column_index * (column_width + column_gap)
        y = y_start
        max_chars = max(32, int(column_width / (font_size * 0.47)))
        for label in labels:
            page.drawString(x, y, ellipsize(label, max_chars))
            y -= leading


def plot_person_reportlab(
    page,
    codigo: str,
    persona: str,
    group: pd.DataFrame,
    course_count: int,
    courses: list[dict[str, object]],
    top_n: int | None,
    page_width: float,
    page_height: float,
) -> None:
    data = group.copy()
    data["score"] = pd.to_numeric(data["score"], errors="coerce").fillna(0)
    data = data[data["score"] > 0]
    if data.empty or float(data["score"].sum()) <= 0:
        plot_empty_page_reportlab(page, codigo, persona, page_width, page_height)
        draw_courses_reportlab(page, courses, x=36, width=page_width - 72, title_y=124)
        return
    data = data.sort_values(["score", "codArea", "codSaber"], ascending=[False, True, True])
    if top_n is not None:
        data = data.head(top_n)
    data = data.sort_values("score", ascending=False)

    total_score = float(data["score"].sum())
    if total_score <= 0:
        plot_empty_page_reportlab(page, codigo, persona, page_width, page_height)
        draw_courses_reportlab(page, courses, x=36, width=page_width - 72, title_y=124)
        return

    page.setFillColor(reportlab_color("#111111"))
    page.setFont("Helvetica-Bold", 16)
    page.drawString(36, page_height - 44, persona)
    page.setFillColor(reportlab_color("#555555"))
    page.setFont("Helvetica", 9)
    subtitle = f"Codigo: {codigo}   |   Saberes: {len(data)}   |   Cursos clasificados: {course_count}"
    page.drawString(36, page_height - 62, subtitle)

    cx, cy, radius = 230, 300, 165
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    start_angle = 90.0
    for row in data.itertuples():
        score = float(row.score)
        extent = -360.0 * score / total_score
        color = AREA_COLORS.get(area_key(row.codArea), "#6B7280")
        page.setFillColor(reportlab_color(color))
        page.setStrokeColor(reportlab_color("#FFFFFF"))
        page.wedge(*bbox, start_angle, extent, stroke=1, fill=1)

        mid_angle = math.radians(start_angle + extent / 2)
        pct = score / total_score
        if pct >= 0.04:
            page.setFillColor(reportlab_color("#FFFFFF"))
            page.setFont("Helvetica-Bold", 8)
            page.drawCentredString(
                cx + math.cos(mid_angle) * radius * 0.62,
                cy + math.sin(mid_angle) * radius * 0.62,
                f"{pct:.0%}",
            )
        page.setFillColor(reportlab_color("#111111"))
        page.setFont("Helvetica", 8)
        page.drawCentredString(
            cx + math.cos(mid_angle) * (radius + 20),
            cy + math.sin(mid_angle) * (radius + 20),
            str(row.codSaber),
        )
        start_angle += extent

    legend_x = 460
    y = page_height - 112
    page.setFillColor(reportlab_color("#111111"))
    page.setFont("Helvetica-Bold", 9)
    page.drawString(legend_x, y, "Saberes")
    y -= 18

    for row in data.itertuples():
        color = AREA_COLORS.get(area_key(row.codArea), "#6B7280")
        page.setFillColor(reportlab_color(color))
        page.rect(legend_x, y - 1, 8, 8, stroke=0, fill=1)
        page.setFillColor(reportlab_color("#111111"))
        label = (
            f"{row.codSaber} - {row.saber}  "
            f"({format_credit_score(float(row.score))}, {float(row.score) / total_score:.0%})"
        )
        y = draw_wrapped_text(page, label, legend_x + 14, y, width=90, font_size=8, leading=9) - 3
        if y < 36:
            break
    draw_courses_reportlab(
        page,
        courses,
        x=legend_x,
        width=page_width - legend_x - 36,
        title_y=y - 8,
    )


def generate_pdf_reportlab(
    saberes: pd.DataFrame,
    cursos_path: Path,
    personas: pd.DataFrame,
    unassigned_courses: list[dict[str, object]],
    output_path: Path,
    top_n: int | None,
) -> None:
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.pdfgen import canvas

    courses_by_person = build_courses_by_person(cursos_path)
    page_width, page_height = landscape(letter)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))
    for row in personas.itertuples(index=False):
        codigo = row.codigo
        persona = row.persona
        courses = courses_by_person.get(codigo, [])
        group = saberes[saberes["codigo"] == codigo]
        if group.empty:
            plot_empty_page_reportlab(page, codigo, persona, page_width, page_height)
            draw_courses_reportlab(page, courses, x=36, width=page_width - 72, title_y=124)
        else:
            plot_person_reportlab(
                page=page,
                codigo=codigo,
                persona=persona,
                group=group,
                course_count=len(courses),
                courses=courses,
                top_n=top_n,
                page_width=page_width,
                page_height=page_height,
            )
        page.showPage()
    draw_unassigned_courses_page_reportlab(
        page=page,
        unassigned_courses=unassigned_courses,
        page_width=page_width,
        page_height=page_height,
    )
    page.showPage()
    page.save()


def generate_pdf(
    saberes_path: Path,
    cursos_path: Path,
    personas_path: Path,
    plan_path: Path,
    output_path: Path,
    top_n: int | None,
) -> None:
    saberes = normalize_saberes_input(read_csv(saberes_path), saberes_path)
    saberes = apply_course_credit_scores(saberes, cursos_path)

    personas = build_person_list(personas_path, saberes)
    courses_by_person = build_courses_by_person(cursos_path)
    unassigned_courses = build_unassigned_courses(plan_path, cursos_path)

    if PdfPages is None:
        generate_pdf_reportlab(
            saberes=saberes,
            cursos_path=cursos_path,
            personas=personas,
            unassigned_courses=unassigned_courses,
            output_path=output_path,
            top_n=top_n,
        )
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_path) as pdf:
        for row in personas.itertuples(index=False):
            codigo = row.codigo
            persona = row.persona
            courses = courses_by_person.get(codigo, [])
            group = saberes[saberes["codigo"] == codigo]
            if group.empty:
                plot_empty_page(pdf, codigo, persona, courses)
            else:
                plot_person(
                    pdf=pdf,
                    codigo=codigo,
                    persona=persona,
                    group=group,
                    course_count=len(courses),
                    courses=courses,
                    top_n=top_n,
                )
        plot_unassigned_courses_page(pdf, unassigned_courses)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate one PDF page per person with saber weights by assigned course credits.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--saberes", type=Path, default=DEFAULT_SABERES_CSV)
    parser.add_argument("--cursos", type=Path, default=DEFAULT_CURSOS_CSV)
    parser.add_argument("--personas", type=Path, default=DEFAULT_PERSONAS_CSV)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_PDF)
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Limit each person plot to the top N saberes by assigned credits.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    generate_pdf(
        saberes_path=args.saberes,
        cursos_path=args.cursos,
        personas_path=args.personas,
        plan_path=args.plan,
        output_path=args.output,
        top_n=args.top_n,
    )
    print(f"PDF generado: {args.output}")


if __name__ == "__main__":
    main()
