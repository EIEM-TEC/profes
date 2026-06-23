from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_PERSONAS_SABERES_CSV = OUTPUT_DIR / "personas_saberes.csv"
DEFAULT_CURSOS_RASGOS_CSV = DATA_DIR / "cursos_rasgos.csv"
DEFAULT_SABERES_CSV = DATA_DIR / "saberes.csv"
DEFAULT_PLAN_CSV = DATA_DIR / "plan_de_estudios.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "personas_cursos.csv"

HIP_ALLOWED_COURSE_ID = "FPH0108"
TRANSVERSAL_OPTIONAL_SABERES = {"MET"}

OUTPUT_COLUMNS = [
    "codigo_persona",
    "persona",
    "id_curso",
    "codigo_curso",
    "curso",
    "semestre",
    "tipo",
    "creditos",
    "saberes_requeridos",
    "saberes_requeridos_nombres",
    "saberes_encontrados",
    "saberes_faltantes",
    "coverage",
    "score_promedio_saberes",
    "score_total_saberes",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path, dtype=str).fillna("")


def split_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def unique_preserving_order(values: list[str]) -> list[str]:
    unique = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        unique.append(value)
        seen.add(value)
    return unique


def validate_person_saberes(personas_saberes: pd.DataFrame) -> None:
    required_columns = {"codigo", "persona", "saberes"}
    missing = required_columns - set(personas_saberes.columns)
    if missing:
        raise ValueError(
            f"Missing columns in personas_saberes: {sorted(missing)}"
        )

    duplicated = []
    for row in personas_saberes.itertuples(index=False):
        codes = split_codes(getattr(row, "saberes"))
        repeated = sorted({code for code in codes if codes.count(code) > 1})
        if repeated:
            duplicated.append(f"{row.codigo}: {';'.join(repeated)}")

    if duplicated:
        raise ValueError(
            "Duplicate saberes per person found in personas_saberes.csv:\n"
            + "\n".join(duplicated)
        )


def build_course_saberes(cursos_rasgos: pd.DataFrame) -> dict[str, list[str]]:
    if not {"id", "codSaber"} <= set(cursos_rasgos.columns):
        raise ValueError("cursos_rasgos.csv must contain id and codSaber columns")

    course_saberes: dict[str, list[str]] = {}
    for row in cursos_rasgos.itertuples(index=False):
        course_id = str(row.id).strip()
        if not course_id:
            continue
        current = course_saberes.setdefault(course_id, [])
        current.extend(split_codes(row.codSaber))

    return {
        course_id: unique_preserving_order(codes)
        for course_id, codes in course_saberes.items()
    }


def effective_required_saberes(course_id: str, required: list[str]) -> list[str] | None:
    if "HIP" in required:
        if course_id == HIP_ALLOWED_COURSE_ID:
            return ["HIP"]
        return None

    non_transversal = [
        code for code in required if code not in TRANSVERSAL_OPTIONAL_SABERES
    ]
    return non_transversal or required


def build_saber_names(saberes: pd.DataFrame) -> dict[str, str]:
    required_columns = {"codSaber", "nombre"}
    missing = required_columns - set(saberes.columns)
    if missing:
        raise ValueError(f"saberes.csv missing columns: {sorted(missing)}")

    saber_names = {}
    for row in saberes.itertuples(index=False):
        code = str(row.codSaber).strip()
        if code and code not in saber_names:
            saber_names[code] = str(row.nombre).strip()
    return saber_names


def assign_person_courses(
    personas_saberes: pd.DataFrame,
    cursos_rasgos: pd.DataFrame,
    saberes: pd.DataFrame,
    plan: pd.DataFrame,
) -> pd.DataFrame:
    validate_person_saberes(personas_saberes)

    if "id" not in plan.columns:
        raise ValueError("plan_de_estudios.csv must contain an id column")

    saber_names = build_saber_names(saberes)
    plan_by_id = {
        str(row.id).strip(): row._asdict()
        for row in plan.itertuples(index=False)
        if str(row.id).strip()
    }
    course_saberes = build_course_saberes(cursos_rasgos)

    rows = []
    for person in personas_saberes.itertuples(index=False):
        person_codes = set(split_codes(person.saberes))
        for course_id, raw_required in course_saberes.items():
            required = effective_required_saberes(course_id, raw_required)
            if not required:
                continue

            missing = [code for code in required if code not in person_codes]
            if missing:
                continue

            course = plan_by_id.get(course_id, {})
            required_labels = [
                f"{code} - {saber_names.get(code, '')}" for code in required
            ]
            rows.append(
                {
                    "codigo_persona": person.codigo,
                    "persona": person.persona,
                    "id_curso": course_id,
                    "codigo_curso": course.get("codigo", ""),
                    "curso": course.get("nombre", ""),
                    "semestre": course.get("semestre", ""),
                    "tipo": course.get("tipo", ""),
                    "creditos": course.get("creditos", ""),
                    "saberes_requeridos": ";".join(required),
                    "saberes_requeridos_nombres": "; ".join(required_labels),
                    "saberes_encontrados": ";".join(required),
                    "saberes_faltantes": "",
                    "coverage": "1.0",
                    "score_promedio_saberes": "1.0",
                    "score_total_saberes": str(len(required)),
                }
            )

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output["_semestre_sort"] = pd.to_numeric(
        output["semestre"], errors="coerce"
    ).fillna(999)
    output = output.sort_values(
        ["persona", "_semestre_sort", "codigo_curso", "id_curso"],
        ascending=[True, True, True, True],
        kind="stable",
    )
    return output.drop(columns=["_semestre_sort"])


def generate_personas_cursos(
    personas_saberes_path: Path,
    cursos_rasgos_path: Path,
    saberes_path: Path,
    plan_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    output = assign_person_courses(
        personas_saberes=read_csv(personas_saberes_path),
        cursos_rasgos=read_csv(cursos_rasgos_path),
        saberes=read_csv(saberes_path),
        plan=read_csv(plan_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    description = """
    Asigna cursos a personas usando la clasificacion manual de
    personas_saberes.csv y los saberes requeridos en cursos_rasgos.csv.

    Una persona puede impartir un curso si cubre todos los saberes requeridos.
    Reglas especiales: HIP solamente asigna el curso FPH0108; MET se trata
    como saber transversal opcional cuando aparece junto a otros saberes.
    """
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(description).strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--personas-saberes", type=Path, default=DEFAULT_PERSONAS_SABERES_CSV)
    parser.add_argument("--cursos-rasgos", type=Path, default=DEFAULT_CURSOS_RASGOS_CSV)
    parser.add_argument("--saberes", type=Path, default=DEFAULT_SABERES_CSV)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_CSV)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = generate_personas_cursos(
        personas_saberes_path=args.personas_saberes,
        cursos_rasgos_path=args.cursos_rasgos,
        saberes_path=args.saberes,
        plan_path=args.plan,
        output_path=args.output,
    )
    people_count = output["codigo_persona"].nunique() if not output.empty else 0
    print(f"Filas generadas: {len(output)}")
    print(f"Personas con cursos: {people_count}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
