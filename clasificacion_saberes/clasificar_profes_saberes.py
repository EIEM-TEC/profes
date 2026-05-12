from __future__ import annotations

import argparse
import re
import textwrap
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

CLIE_URLS = {
    "saberes": "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/rasgos_ejes/saberes.csv",
    "cursos_rasgos": "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/cursos/cursos_rasgos.csv",
    "areas": "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/areas.csv",
    "plan_de_estudios": "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/cursos/plan_de_estudios.csv",
}

LOCAL_FILES = {
    "personas": ROOT_DIR / "00_datos.csv",
    "educacion": ROOT_DIR / "01_grados.csv",
    "experiencia": ROOT_DIR / "02_experiencia_industria.csv",
    "areas_interes": ROOT_DIR / "04_areas_interes.csv",
    "cursos_impartidos": ROOT_DIR / "05_cursos.csv",
    "publicaciones": ROOT_DIR / "06_publicaciones.csv",
    "proyectos": ROOT_DIR / "08_proyectos_inv_ext.csv",
}

# These weights express how direct each CV section is as evidence of a saber.
# They are deliberately visible and easy to tune.
SOURCE_WEIGHTS = {
    "educacion": 3.0,
    "areas_interes": 2.2,
    "cursos_impartidos": 2.4,
    "experiencia": 1.4,
    "publicaciones": 1.6,
    "proyectos": 1.2,
}

DEFAULT_SECTIONS = "educacion,publicaciones"

STOPWORDS = {
    "a",
    "al",
    "and",
    "aplicada",
    "aplicadas",
    "aplicado",
    "aplicados",
    "con",
    "de",
    "del",
    "e",
    "el",
    "en",
    "for",
    "i",
    "ii",
    "iii",
    "ingenieria",
    "ingenierias",
    "la",
    "las",
    "los",
    "of",
    "para",
    "por",
    "the",
    "un",
    "una",
    "y",
}

GENERIC_TOKENS = {
    "analisis",
    "aplicaciones",
    "ciencias",
    "control",
    "desarrollo",
    "diseno",
    "gestion",
    "ingenieria",
    "integracion",
    "laboratorio",
    "modelado",
    "sistema",
    "sistemas",
}

SABER_ALIASES = {
    "MAT": [
        "matematica",
        "calculo",
        "algebra",
        "ecuaciones diferenciales",
        "calculo superior",
    ],
    "FIS": ["fisica", "mecanica clasica"],
    "QUI": ["quimica"],
    "ECS": ["etica", "ciencias sociales", "estudios costarricenses"],
    "HIP": ["habilidades interpersonales", "relaciones laborales"],
    "EMP": ["emprendedurismo", "emprendedores", "administracion de empresas", "negocios"],
    "ADP": [
        "administracion de proyectos",
        "gestion de proyectos",
        "proyectos de construccion",
        "ingeniero de proyectos",
    ],
    "COE": ["comunicacion oral", "comunicacion escrita", "redaccion"],
    "ING": ["ingles", "english"],
    "DPI": ["dibujo tecnico", "dibujo industrial", "cad", "planos", "revit"],
    "CEE": [
        "circuitos electricos",
        "electricidad",
        "electronica",
        "electronica analogica",
        "electronica digital",
        "potencia electrica",
    ],
    "MEE": [
        "maquinas electricas",
        "motores electricos",
        "transformadores",
        "turbomaquinas",
    ],
    "IYT": [
        "instrumentacion",
        "transductores",
        "sensores",
        "adquisicion de datos",
        "microsistemas",
    ],
    "CIM": [
        "materiales",
        "ciencia de materiales",
        "ingenieria de materiales",
        "caracterizacion de materiales",
        "superficies",
        "tribologia",
        "metalurgia",
    ],
    "MSF": [
        "mecanica",
        "solidos",
        "fluidos",
        "estatica",
        "dinamica",
        "resistencia de materiales",
        "estructuras",
        "principios estructurales",
    ],
    "TTC": [
        "termodinamica",
        "transferencia de calor",
        "sistemas termicos",
        "refrigeracion",
        "aire acondicionado",
        "hvac",
        "climatizacion",
        "energia termica",
    ],
    "EDM": [
        "elementos de maquinas",
        "diseno mecanico",
        "mecanismos",
        "maquinas y equipos",
        "mecanica de precision",
    ],
    "MAN": [
        "manufactura",
        "procesos de manufactura",
        "manufactura aditiva",
        "fabricacion",
        "mecanizado",
        "impresion 3d",
    ],
    "PRO": [
        "programacion",
        "software",
        "computacion",
        "informatica",
        "ciencia de datos",
        "desarrollador de software",
    ],
    "MYS": [
        "modelado",
        "simulacion",
        "metodos numericos",
        "elementos finitos",
        "simulacion computacional",
    ],
    "MAC": [
        "microcontroladores",
        "arquitectura de computadores",
        "computadores",
        "sistemas embebidos",
        "sistema embebido",
        "iot",
        "firmware",
    ],
    "SCA": [
        "control automatico",
        "sistemas de control",
        "automatizacion",
        "control electrico",
        "eventos discretos",
    ],
    "EYD": [
        "estadistica",
        "diseno de experimentos",
        "analisis de datos",
        "ciencia de datos",
        "data science",
    ],
    "CDM": [
        "confiabilidad",
        "disponibilidad",
        "mantenibilidad",
        "mantenimiento predictivo",
        "gestion de activos",
        "diagnostico",
        "pronostico",
        "fallas",
    ],
    "MET": ["metrologia", "medicion", "calibracion"],
    "IEM": [
        "instalaciones electromecanicas",
        "instalaciones electricas",
        "instalaciones mecanicas",
        "edificaciones",
        "aire comprimido",
        "mecanico sanitarias",
        "sistemas contra incendios",
        "puesta a tierra",
    ],
    "GAE": [
        "generacion de energia",
        "almacenamiento de energia",
        "baterias",
        "energias renovables",
        "energia solar",
        "energia eolica",
        "energia oceanica",
        "energias limpias",
    ],
    "DTE": [
        "distribucion de energia",
        "transmision de energia",
        "sistemas electricos de potencia",
        "baja tension",
        "media tension",
        "alta tension",
    ],
    "GCV": [
        "ciclo de vida",
        "transformacion digital",
        "gestion de mantenimiento",
        "mantenimiento electromecanico",
        "gestion de activos",
    ],
    "GEE": [
        "gestion de la energia",
        "eficiencia energetica",
        "ahorro energetico",
        "mercados energeticos",
    ],
    "LID": ["liderazgo", "inclusion", "administracion"],
    "SYC": ["sostenibilidad", "impacto social", "ambiental"],
    "IPR": ["investigacion", "extension", "publicacion", "presentacion de resultados"],
    "ADC": ["avionica", "dinamica de vuelo", "control de vuelo", "satelites", "cubesat"],
    "ACP": ["aerodinamica", "propulsion", "aeroespacial", "aeronautica"],
    "AME": [
        "estructuras de aeronave",
        "mecanismos de aeronave",
        "materiales en aeronautica",
        "mecanica aeronautica",
    ],
    "GCA": ["ciclo de vida de la aeronave", "sistemas de la aeronave"],
    "SAA": ["seguridad aeronautica", "aeronavegabilidad", "metrologia aeronautica"],
    "ASE": ["sistemas embebidos", "aplicaciones embebidas", "iot", "firmware"],
    "AYD": ["automatizacion industrial", "digitalizacion industrial", "transformacion digital"],
    "RBT": ["robotica", "robots", "sistemas autonomos", "transporte autonomo"],
    "MNC": ["modelado numerico", "simulacion computacional", "elementos finitos"],
    "ISC": [
        "sistemas complejos",
        "ingenieria de sistemas",
        "integracion de sistemas",
        "sistemas ciberfisicos",
    ],
    "AIA": [
        "inteligencia artificial",
        "machine learning",
        "aprendizaje automatico",
        "vision de maquina",
        "analisis predictivo",
    ],
    "CIS": [
        "ciberseguridad",
        "seguridad informatica",
        "telematica",
        "redes informaticas",
        "redes de computadores",
        "ics",
        "bacnet",
        "intrusion detection",
    ],
}

AREA_ALIASES = {
    "ADD": ["analisis de datos", "estadistica", "confiabilidad"],
    "AER": ["aeronautica", "aeroespacial", "aeronave"],
    "AUT": ["automatica", "control", "automatizacion", "mecatronica"],
    "CIB": ["matematica", "fisica", "quimica", "ciencias basicas"],
    "CYD": ["comunicacion", "dibujo", "ingles"],
    "FPH": ["administracion", "emprendimiento", "relaciones laborales"],
    "IEE": ["electricidad", "electrica", "electronica", "potencia"],
    "IMM": ["mecanica", "materiales", "manufactura", "diseno mecanico"],
    "INS": ["instalaciones", "mantenimiento industrial", "gestion de energia"],
    "SCF": [],
}


@dataclass(frozen=True)
class Evidence:
    source: str
    text: str
    weight: float


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(value: object) -> list[str]:
    return [
        token
        for token in normalize_text(value).split()
        if len(token) > 2 and token not in STOPWORDS
    ]


def clean_output_text(value: object, max_len: int = 160) -> str:
    if value is None or pd.isna(value):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def normalized_phrase(value: str) -> str:
    return " ".join(tokenize(value))


def phrase_weight(phrase: str, base: float) -> float:
    token_count = len(phrase.split())
    return base * min(2.5, 0.8 + token_count * 0.35)


def download_file(name: str, refresh: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{name}.csv"
    if path.exists() and not refresh:
        return path
    with urlopen(CLIE_URLS[name], timeout=30) as response:
        data = response.read()
    path.write_bytes(data)
    return path


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path).fillna("")


def load_clie_data(refresh: bool = False) -> dict[str, pd.DataFrame]:
    return {
        name: read_csv(download_file(name, refresh=refresh))
        for name in CLIE_URLS
    }


def load_local_data() -> dict[str, pd.DataFrame]:
    missing = [str(path) for path in LOCAL_FILES.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing local CSV files:\n" + "\n".join(missing))
    return {name: read_csv(path) for name, path in LOCAL_FILES.items()}


def split_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def clipped_join(values: list[str], limit: int = 5) -> str:
    unique = []
    seen = set()
    for value in values:
        value = clean_output_text(value)
        if value and value not in seen:
            unique.append(value)
            seen.add(value)
    if len(unique) <= limit:
        return " | ".join(unique)
    return " | ".join(unique[:limit]) + f" | +{len(unique) - limit} more"


def build_course_saberes(cursos_rasgos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in cursos_rasgos.iterrows():
        for cod_saber in split_codes(row["codSaber"]):
            rows.append({"id": row["id"], "codSaber": cod_saber})
    return pd.DataFrame(rows)


def build_saber_profiles(
    saberes: pd.DataFrame,
    areas: pd.DataFrame,
    cursos_rasgos: pd.DataFrame,
    plan: pd.DataFrame,
) -> dict[str, dict[str, object]]:
    area_name = dict(zip(areas["codArea"], areas["nombre"]))
    saberes_enriched = saberes.copy()
    saberes_enriched["area"] = saberes_enriched["codArea"].map(area_name).fillna("")
    course_saberes = build_course_saberes(cursos_rasgos)
    course_names = course_saberes.merge(
        plan[["id", "codigo", "nombre"]],
        on="id",
        how="left",
    )

    profiles: dict[str, dict[str, object]] = {}
    for cod_saber, group in saberes_enriched.groupby("codSaber", sort=False):
        saber_name = group.iloc[0]["nombre"]
        area_codes = sorted(group["codArea"].drop_duplicates().tolist())
        area_names = [area_name.get(cod_area, "") for cod_area in area_codes]
        terms: dict[str, float] = {}

        def add_term(term: str, base: float) -> None:
            phrase = normalized_phrase(term)
            if not phrase:
                return
            if len(phrase.split()) == 1 and phrase in GENERIC_TOKENS:
                return
            terms[phrase] = max(terms.get(phrase, 0.0), phrase_weight(phrase, base))

        add_term(saber_name, 2.2)
        if len(area_codes) == 1:
            for cod_area in area_codes:
                add_term(area_name.get(cod_area, ""), 0.7)
                for alias in AREA_ALIASES.get(cod_area, []):
                    add_term(alias, 0.75)
        for alias in SABER_ALIASES.get(cod_saber, []):
            add_term(alias, 1.6)

        related_courses = course_names[course_names["codSaber"] == cod_saber]
        for _, course in related_courses.iterrows():
            add_term(course.get("nombre", ""), 0.8)
            add_term(course.get("codigo", ""), 0.4)

        profile_tokens = set()
        for phrase in terms:
            for token in phrase.split():
                if token not in GENERIC_TOKENS:
                    profile_tokens.add(token)

        profiles[cod_saber] = {
            "codArea": ";".join(area_codes),
            "area": "; ".join(area for area in area_names if area),
            "saber": saber_name,
            "terms": terms,
            "tokens": profile_tokens,
        }
    return profiles


def build_saber_lookup(saberes: pd.DataFrame, areas: pd.DataFrame) -> pd.DataFrame:
    area_name = dict(zip(areas["codArea"], areas["nombre"]))
    enriched = saberes.copy()
    enriched["area"] = enriched["codArea"].map(area_name).fillna("")
    rows = []
    for cod_saber, group in enriched.groupby("codSaber", sort=False):
        rows.append(
            {
                "codSaber": cod_saber,
                "saber": group.iloc[0]["nombre"],
                "codArea": ";".join(sorted(group["codArea"].drop_duplicates().tolist())),
                "area": "; ".join(
                    area
                    for area in sorted(group["area"].drop_duplicates().tolist())
                    if area
                ),
            }
        )
    return pd.DataFrame(rows)


def build_person_evidence(local: dict[str, pd.DataFrame], sections: set[str]) -> dict[str, list[Evidence]]:
    evidence: dict[str, list[Evidence]] = defaultdict(list)

    if "educacion" in sections:
        for _, row in local["educacion"].iterrows():
            text = " ".join(
                [
                    str(row.get("grado", "")),
                    str(row.get("campo", "")),
                    str(row.get("institucion", "")),
                ]
            )
            evidence[row["codigo"]].append(Evidence("educacion", text, SOURCE_WEIGHTS["educacion"]))

    if "areas_interes" in sections:
        for _, row in local["areas_interes"].iterrows():
            evidence[row["codigo"]].append(
                Evidence("areas_interes", row.get("area", ""), SOURCE_WEIGHTS["areas_interes"])
            )

    if "cursos_impartidos" in sections:
        for _, row in local["cursos_impartidos"].iterrows():
            text = f"{row.get('codCurso', '')} {row.get('curso', '')}"
            evidence[row["codigo"]].append(
                Evidence("cursos_impartidos", text, SOURCE_WEIGHTS["cursos_impartidos"])
            )

    if "experiencia" in sections:
        for _, row in local["experiencia"].iterrows():
            text = " ".join(
                [
                    str(row.get("empresa", "")),
                    str(row.get("puesto", "")),
                    str(row.get("descripcion", "")),
                ]
            )
            evidence[row["codigo"]].append(Evidence("experiencia", text, SOURCE_WEIGHTS["experiencia"]))

    if "publicaciones" in sections:
        for _, row in local["publicaciones"].iterrows():
            text = str(row.get("titulo", ""))
            evidence[row["codigo"]].append(
                Evidence("publicaciones", text, SOURCE_WEIGHTS["publicaciones"])
            )

    if "proyectos" in sections:
        for _, row in local["proyectos"].iterrows():
            text = " ".join(
                [
                    str(row.get("proyecto", "")),
                    str(row.get("tipo", "")),
                    str(row.get("nombre", "")),
                ]
            )
            for codigo in split_codes(row.get("codigo", "")):
                evidence[codigo].append(Evidence("proyectos", text, SOURCE_WEIGHTS["proyectos"]))

    return evidence


def classify_person_saberes(
    personas: pd.DataFrame,
    evidence_by_person: dict[str, list[Evidence]],
    profiles: dict[str, dict[str, object]],
    min_score: float,
) -> pd.DataFrame:
    rows = []
    for _, person in personas.iterrows():
        codigo = person["codigo"]
        person_evidence = evidence_by_person.get(codigo, [])

        for cod_saber, profile in profiles.items():
            score = 0.0
            matched_terms: list[str] = []
            evidence_snippets: list[str] = []
            matched_sources = set()

            terms: dict[str, float] = profile["terms"]  # type: ignore[assignment]
            profile_tokens: set[str] = profile["tokens"]  # type: ignore[assignment]

            for evidence in person_evidence:
                text_norm = normalize_text(evidence.text)
                if not text_norm:
                    continue
                bounded_text = f" {text_norm} "
                text_tokens = set(tokenize(evidence.text))

                local_hits = []
                for phrase, weight in terms.items():
                    if phrase and f" {phrase} " in bounded_text:
                        contribution = evidence.weight * weight
                        score += contribution
                        local_hits.append(phrase)

                overlap = profile_tokens & text_tokens
                if len(overlap) >= 2 and len(profile_tokens) >= 2:
                    ratio = len(overlap) / len(profile_tokens)
                    if ratio >= 0.35:
                        contribution = evidence.weight * ratio * 0.8
                        score += contribution
                        local_hits.append("tokens:" + ",".join(sorted(overlap)[:6]))

                if local_hits:
                    matched_sources.add(evidence.source)
                    matched_terms.extend(local_hits)
                    evidence_snippets.append(f"{evidence.source}: {evidence.text}")

            if score >= min_score:
                rows.append(
                    {
                        "codigo": codigo,
                        "persona": person["nombre"],
                        "codArea": profile["codArea"],
                        "area": profile["area"],
                        "codSaber": cod_saber,
                        "saber": profile["saber"],
                        "score": round(score, 2),
                        "fuentes_cv": ";".join(sorted(matched_sources)),
                        "terminos_match": clipped_join(matched_terms, limit=10),
                        "evidencia": clipped_join(evidence_snippets, limit=4),
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "codigo",
                "persona",
                "codArea",
                "area",
                "codSaber",
                "saber",
                "score",
                "fuentes_cv",
                "terminos_match",
                "evidencia",
            ]
        )

    return pd.DataFrame(rows).sort_values(
        ["persona", "score", "codArea", "codSaber"],
        ascending=[True, False, True, True],
    )


def summarize_person_saberes(person_saberes: pd.DataFrame) -> pd.DataFrame:
    if person_saberes.empty:
        return pd.DataFrame(columns=["codigo", "persona", "saberes", "saberes_nombres"])

    rows = []
    for (codigo, persona), group in person_saberes.groupby(["codigo", "persona"], sort=False):
        ordered = group.sort_values(["codArea", "codSaber"])
        rows.append(
            {
                "codigo": codigo,
                "persona": persona,
                "saberes": ";".join(ordered["codSaber"].tolist()),
                "saberes_nombres": "; ".join(
                    f"{row.codSaber} - {row.saber}" for row in ordered.itertuples()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("persona")


def classify_courses(
    personas: pd.DataFrame,
    person_saberes: pd.DataFrame,
    saberes: pd.DataFrame,
    areas: pd.DataFrame,
    cursos_rasgos: pd.DataFrame,
    plan: pd.DataFrame,
    min_coverage: float,
) -> pd.DataFrame:
    course_saberes = build_course_saberes(cursos_rasgos)
    saber_names = build_saber_lookup(saberes, areas)
    course_saberes = course_saberes.merge(saber_names, on="codSaber", how="left")

    course_info = plan[
        ["id", "semestre", "codigo", "nombre", "tipo", "creditos", "HC", "HE"]
    ].rename(columns={"codigo": "codigo_curso", "nombre": "curso"})

    person_scores = {
        codigo: dict(zip(group["codSaber"], group["score"]))
        for codigo, group in person_saberes.groupby("codigo")
    }

    rows = []
    for _, person in personas.iterrows():
        codigo_persona = person["codigo"]
        scores = person_scores.get(codigo_persona, {})
        if not scores:
            continue

        for course_id, req_group in course_saberes.groupby("id"):
            required = req_group["codSaber"].tolist()
            matched = [cod for cod in required if cod in scores]
            if not required:
                continue
            coverage = len(matched) / len(required)
            if coverage < min_coverage:
                continue

            missing = [cod for cod in required if cod not in scores]
            course = course_info[course_info["id"] == course_id]
            course_row = course.iloc[0].to_dict() if not course.empty else {}

            req_labels = [
                f"{row.codSaber} - {row.saber}" for row in req_group.sort_values("codSaber").itertuples()
            ]
            rows.append(
                {
                    "codigo_persona": codigo_persona,
                    "persona": person["nombre"],
                    "id_curso": course_id,
                    "codigo_curso": course_row.get("codigo_curso", ""),
                    "curso": course_row.get("curso", ""),
                    "semestre": course_row.get("semestre", ""),
                    "tipo": course_row.get("tipo", ""),
                    "creditos": course_row.get("creditos", ""),
                    "saberes_requeridos": ";".join(required),
                    "saberes_requeridos_nombres": "; ".join(req_labels),
                    "saberes_encontrados": ";".join(matched),
                    "saberes_faltantes": ";".join(missing),
                    "coverage": round(coverage, 3),
                    "score_promedio_saberes": round(sum(scores[cod] for cod in matched) / len(matched), 2)
                    if matched
                    else 0.0,
                    "score_total_saberes": round(sum(scores[cod] for cod in matched), 2),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
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
        )

    return pd.DataFrame(rows).sort_values(
        ["persona", "coverage", "score_total_saberes", "semestre", "codigo_curso"],
        ascending=[True, False, False, True, True],
    )


def summarize_person_courses(person_courses: pd.DataFrame) -> pd.DataFrame:
    if person_courses.empty:
        return pd.DataFrame(columns=["codigo_persona", "persona", "cursos"])
    rows = []
    for (codigo, persona), group in person_courses.groupby(["codigo_persona", "persona"], sort=False):
        courses = group.sort_values(["semestre", "codigo_curso"])
        rows.append(
            {
                "codigo_persona": codigo,
                "persona": persona,
                "cursos": "; ".join(
                    f"{row.codigo_curso} - {row.curso}" for row in courses.itertuples()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("persona")


def parse_sections(value: str) -> set[str]:
    sections = {part.strip() for part in value.split(",") if part.strip()}
    unknown = sections - set(SOURCE_WEIGHTS)
    if unknown:
        valid = ", ".join(SOURCE_WEIGHTS)
        raise ValueError(f"Unknown sections {sorted(unknown)}. Valid sections: {valid}")
    return sections


def write_outputs(
    person_saberes: pd.DataFrame,
    person_courses: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    person_saberes.to_csv(OUTPUT_DIR / "personas_saberes.csv", index=False, encoding="utf-8-sig")
    summarize_person_saberes(person_saberes).to_csv(
        OUTPUT_DIR / "personas_saberes_resumen.csv",
        index=False,
        encoding="utf-8-sig",
    )
    person_courses.to_csv(OUTPUT_DIR / "personas_cursos.csv", index=False, encoding="utf-8-sig")
    summarize_person_courses(person_courses).to_csv(
        OUTPUT_DIR / "personas_cursos_resumen.csv",
        index=False,
        encoding="utf-8-sig",
    )


def build_parser() -> argparse.ArgumentParser:
    description = """
    Clasifica profesores por saberes CLIE usando la evidencia textual de sus CVs
    en este repositorio y luego propone cursos que pueden impartir segun los
    saberes requeridos por cada curso.
    """
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(description).strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Vuelve a descargar los CSV fuente de CLIE aunque ya existan en data/.",
    )
    parser.add_argument(
        "--sections",
        default=DEFAULT_SECTIONS,
        help="Secciones del CV a usar, separadas por coma.",
    )
    parser.add_argument(
        "--min-saber-score",
        type=float,
        default=4.0,
        help="Puntaje minimo para aceptar que una persona tiene un saber.",
    )
    parser.add_argument(
        "--min-course-coverage",
        type=float,
        default=1.0,
        help="Fraccion minima de saberes requeridos que la persona debe cubrir para el curso.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    sections = parse_sections(args.sections)

    clie = load_clie_data(refresh=args.refresh)
    local = load_local_data()

    profiles = build_saber_profiles(
        saberes=clie["saberes"],
        areas=clie["areas"],
        cursos_rasgos=clie["cursos_rasgos"],
        plan=clie["plan_de_estudios"],
    )
    evidence = build_person_evidence(local, sections)
    person_saberes = classify_person_saberes(
        personas=local["personas"],
        evidence_by_person=evidence,
        profiles=profiles,
        min_score=args.min_saber_score,
    )
    person_courses = classify_courses(
        personas=local["personas"],
        person_saberes=person_saberes,
        saberes=clie["saberes"],
        areas=clie["areas"],
        cursos_rasgos=clie["cursos_rasgos"],
        plan=clie["plan_de_estudios"],
        min_coverage=args.min_course_coverage,
    )
    write_outputs(person_saberes, person_courses)

    print(f"Saberes persona-saber: {len(person_saberes)} filas")
    print(f"Cursos persona-curso: {len(person_courses)} filas")
    print(f"Outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
