from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_SABERES_CSV = OUTPUT_DIR / "personas_saberes.csv"
DEFAULT_CURSOS_CSV = OUTPUT_DIR / "personas_cursos.csv"
DEFAULT_PERSONAS_CSV = ROOT_DIR / "00_datos.csv"
DEFAULT_PDF = OUTPUT_DIR / "personas_saberes_graficos.pdf"

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


def build_person_list(personas_path: Path, saberes: pd.DataFrame) -> pd.DataFrame:
    if personas_path.exists():
        personas = read_csv(personas_path)[["codigo", "nombre"]].rename(columns={"nombre": "persona"})
        return personas.sort_values("persona")
    return saberes[["codigo", "persona"]].drop_duplicates().sort_values("persona")


def build_course_counts(cursos_path: Path) -> dict[str, int]:
    if not cursos_path.exists():
        return {}
    cursos = read_csv(cursos_path)
    if "codigo_persona" not in cursos.columns:
        return {}
    return cursos.groupby("codigo_persona").size().to_dict()


def plot_empty_page(pdf: PdfPages, codigo: str, persona: str) -> None:
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
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def plot_person(
    pdf: PdfPages,
    codigo: str,
    persona: str,
    group: pd.DataFrame,
    course_count: int,
    top_n: int | None,
) -> None:
    data = group.copy()
    data["score"] = pd.to_numeric(data["score"], errors="coerce").fillna(0)
    data = data.sort_values(["score", "codArea", "codSaber"], ascending=[False, True, True])
    if top_n is not None:
        data = data.head(top_n)
    data = data.sort_values("score", ascending=False)

    labels = [str(row.codSaber) for row in data.itertuples()]
    legend_labels = [wrap_label(f"{row.codSaber} - {row.saber}", width=42) for row in data.itertuples()]
    colors = [AREA_COLORS.get(area_key(row.codArea), "#6B7280") for row in data.itertuples()]

    fig, ax = plt.subplots(figsize=(11, 8.5))
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
    subtitle = f"Codigo: {codigo}   |   Saberes: {len(group)}   |   Cursos clasificados: {course_count}"
    ax.text(0, 1.01, subtitle, transform=ax.transAxes, fontsize=9, color="#555555")

    total_score = float(data["score"].sum())
    legend_with_scores = [
        f"{label}  ({score:.2f}, {score / total_score:.0%})"
        for label, score in zip(legend_labels, data["score"], strict=False)
    ]
    ax.legend(
        wedges,
        legend_with_scores,
        title="Saberes",
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=8,
        title_fontsize=9,
    )

    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def generate_pdf(
    saberes_path: Path,
    cursos_path: Path,
    personas_path: Path,
    output_path: Path,
    top_n: int | None,
) -> None:
    saberes = read_csv(saberes_path)
    required_columns = {"codigo", "persona", "codArea", "codSaber", "saber", "score"}
    missing = required_columns - set(saberes.columns)
    if missing:
        raise ValueError(f"Missing columns in {saberes_path}: {sorted(missing)}")

    personas = build_person_list(personas_path, saberes)
    course_counts = build_course_counts(cursos_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_path) as pdf:
        for row in personas.itertuples(index=False):
            codigo = row.codigo
            persona = row.persona
            group = saberes[saberes["codigo"] == codigo]
            if group.empty:
                plot_empty_page(pdf, codigo, persona)
            else:
                plot_person(
                    pdf=pdf,
                    codigo=codigo,
                    persona=persona,
                    group=group,
                    course_count=course_counts.get(codigo, 0),
                    top_n=top_n,
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate one PDF page per person with classified saber scores.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--saberes", type=Path, default=DEFAULT_SABERES_CSV)
    parser.add_argument("--cursos", type=Path, default=DEFAULT_CURSOS_CSV)
    parser.add_argument("--personas", type=Path, default=DEFAULT_PERSONAS_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_PDF)
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Limit each person plot to the top N saberes by score.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    generate_pdf(
        saberes_path=args.saberes,
        cursos_path=args.cursos,
        personas_path=args.personas,
        output_path=args.output,
        top_n=args.top_n,
    )
    print(f"PDF generado: {args.output}")


if __name__ == "__main__":
    main()
