import pandas as pd
import yaml
import os
from datetime import date, datetime

today = date.today()


def read_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def has_any_value(row, columns):
    return any(clean_text(row.get(column, "")) for column in columns)


def int_or_zero(value):
    value = clean_text(value)
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


# === Cargar los csv con los datos de los profes ===
datos = read_csv("00_datos.csv")
grados = read_csv("01_grados.csv")
experi = read_csv("02_experiencia_industria.csv")
idiomas = read_csv("03_idiomas.csv")
areas = read_csv("04_areas_interes.csv")
cursos = read_csv("05_cursos.csv")
publicaciones = read_csv("06_publicaciones.csv")
carrera = read_csv("07_carrera.csv")
proyect = read_csv("08_proyectos_inv_ext.csv")
proyect["codigo"] = proyect["codigo"].apply(
    lambda value: [codigo.strip() for codigo in clean_text(value).split(";") if codigo.strip()]
)
proyect = proyect.explode("codigo")
habilil = read_csv("09_habilidades.csv")
membres = read_csv("10_membresias.csv")
                

# === Step 2: Create output folder ===
output_dir = "yamls"
os.makedirs(output_dir, exist_ok=True)

def convert_cr_to_iso(date_cr):
    date_cr = clean_text(date_cr)
    if not date_cr or date_cr == "present":
        return date_cr
    try:
        return datetime.strptime(date_cr, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return date_cr

def make_education_entries(grados):
    education_entries = []
    for _, row in grados.iterrows():
        if not has_any_value(row, ["grado", "campo", "institucion", "pais", "año"]):
            continue
        entry = {
            "institution": clean_text(row["institucion"]),
            "area": clean_text(row["campo"]),
            "degree": clean_text(row["grado"]),
            "location": clean_text(row["pais"]),
            "end_date": clean_text(row["año"]),
        }
        education_entries.append(entry)
    return education_entries

def make_career_entries(carrera):
    career_entries = []
    for _, row in carrera.iterrows():
        if not has_any_value(row, ["categoria", "fecha"]):
            continue
        entry = {
            "name": clean_text(row["categoria"]),
            "date": clean_text(row["fecha"]),
        }
        career_entries.append(entry)
    return career_entries


def make_publication_date(row):
    year = int_or_zero(row.get("año", ""))
    month = int_or_zero(row.get("mes", ""))
    day = int_or_zero(row.get("dia", ""))

    if not year:
        return ""
    if day and month:
        return f"{day:02d}/{month:02d}/{year}"
    if month:
        return f"{month}/{year}"
    return f"{year}"

def make_publication_entries(publicaciones):
    publication_entries = []
    for _, row in publicaciones.iterrows():
        if not has_any_value(row, ["titulo", "revista", "autores", "año", "doi"]):
            continue
        autoresd = clean_text(row.get("autores","")).split(";")
        autores = [x.strip() for x in autoresd]
        entry = {
            "title": clean_text(row["titulo"]),
            "journal": clean_text(row["revista"]),
            "authors": autores,
            "date": make_publication_date(row),
            "doi": clean_text(row["doi"])
        }
        publication_entries.append(entry)
    return publication_entries

def make_courses_entries(cursos):
    courses_entries = []
    for _, row in cursos.iterrows():
        if not has_any_value(row, ["codCurso", "curso"]):
            continue
        entry = {
            "bullet": f"{clean_text(row['codCurso'])} - {clean_text(row['curso'])}"
        }
        courses_entries.append(entry)
    return courses_entries

def make_research_entries(proyect):
    research_entries = []
    for _, row in proyect.iterrows():
        if not has_any_value(row, ["numProy", "proyecto", "inicio", "fin", "tipo", "nombre"]):
            continue
        entry = {
            "name": clean_text(row["proyecto"]),
            "start_date": convert_cr_to_iso(row["inicio"]),
            "end_date": convert_cr_to_iso(row["fin"]),
            "highlights": [
                f"**Numero:** {clean_text(row['numProy'])}",
                f"**Tipo:** {clean_text(row['tipo'])}",
                f"**Escuela:** {clean_text(row['nombre'])}"    
            ]        
        }
        research_entries.append(entry)
    return research_entries

def make_experience_entries(experi):
    experi_entries = []
    for _, row in experi.iterrows():
        if not has_any_value(row, ["empresa", "puesto", "inicio", "fin", "descripcion"]):
            continue
        entry = {
            "company": clean_text(row["empresa"]),
            "position": clean_text(row["puesto"]),
            "start_date": convert_cr_to_iso(row["inicio"]),
            "end_date": convert_cr_to_iso(row["fin"]),
            "summary": clean_text(row["descripcion"])
        }
        experi_entries.append(entry)
    return experi_entries  

def make_language_entries(idiomas):
    idiom_entries = []
    for _, row in idiomas.iterrows():
        if not has_any_value(row, ["idioma", "detalle"]):
            continue
        entry = {
            "bullet": f"{clean_text(row['idioma'])}: {clean_text(row['detalle'])}"
        }
        idiom_entries.append(entry)
    return idiom_entries  

def make_interest_entries(areas):
    area_entries = []
    for _, row in areas.iterrows():
        if not has_any_value(row, ["area"]):
            continue
        entry = {
            "bullet": clean_text(row["area"])
        }
        area_entries.append(entry)
    return area_entries 

def make_rendercv_yaml(id,datos,grados):
    print(clean_text(datos.nombre))
    nombre = clean_text(datos.nombre)
    titulo = clean_text(datos.titulo)
    match titulo:
            case "M.Sc." | "Lic." | "Ing." | "Máster" | "Dr.-Ing." | "Mag.":
                nombre =  f"{titulo} {nombre}"
            case "Ph.D.":
                nombre = f"{nombre}, {titulo}"
    education = make_education_entries(grados[grados["codigo"]==id])
    career = make_career_entries(carrera[carrera["codigo"]==id])
    public = make_publication_entries(publicaciones[publicaciones["codigo"]==id])
    research = make_research_entries(proyect[proyect["codigo"]==id])
    experie = make_experience_entries(experi[experi["codigo"]==id])
    languag = make_language_entries(idiomas[idiomas["codigo"]==id])
    interes = make_interest_entries(areas[areas["codigo"]==id])
    cursoss = make_courses_entries(cursos[cursos["codigo"]==id])
    info_laboral = []
    for label, column in [
        ("Cédula", "cedula"),
        ("Tipo de nombramiento", "tipoNom"),
        ("Fecha de contratación", "fechaCon"),
        ("Sede", "sede"),
        ("Escuela", "escuela"),
        ("Correo", "correo"),
        ("ORCID", "orcid"),
    ]:
        details = clean_text(datos[column])
        if column == "orcid" and details == "00":
            details = "N/A"
        if details:
            info_laboral.append({"label": label, "details": details})

    sections = {}
    if info_laboral:
        sections["Información laboral"] = info_laboral
    if education:
        sections["Educación"] = education
    if career:
        sections["Carrera profesional"] = career
    if experie:
        sections["Experiencia"] = experie
    if languag:
        sections["Idiomas"] = languag
    if interes:
        sections["Áreas de interés"] = interes
    # if cursoss:
    #     sections["Cursos impartidos en los últimos tres años"] = cursoss
    if public:
        sections["Publicaciones"] = public
    if research:
        sections["Proyectos de investigación y extensión"] = research

    cv = {
        "name": nombre,
        "sections": sections,
    }
    correo = clean_text(datos["correo"])
    telefono = clean_text(datos["telefono"])
    if correo:
        cv["email"] = correo
    if telefono:
        cv["phone"] = f"+506-{telefono}"

    yaml_dict = {
        "cv": cv,
        "locale": {
            "language": "spanish",
            "present": "actualmente",
        },
        "settings": {
            "current_date": today.isoformat(),
            "render_command": {
                "output_folder": "../CVs",
                "dont_generate_html": True,
                "dont_generate_markdown": True,
                "dont_generate_png": True
            }
        },
        "design": {
            "theme": "engineeringresumes",
            "page": {
                "show_footer": True
            },
            "templates": {
                "footer": "NAME - Página PAGE_NUMBER de TOTAL_PAGES",
                "top_note": "Última actualización: DAY_IN_TWO_DIGITS/MONTH_IN_TWO_DIGITS/YEAR",
                "education_entry": {
                    "main_column": '**INSTITUTION**, DEGREE_WITH_AREA\nSUMMARY\nHIGHLIGHTS',
                    "date_and_location_column": "DATE"
                },
                "experience_entry": {
                    "date_and_location_column": "DATE"
                }
            }
        }
    }
    return yaml_dict, f"{id}.yml"

# === Step 4: Generate YAML files for all employees ===
for _, row in datos.iterrows():
    id = row["codigo"]
    yaml_dict, filename = make_rendercv_yaml(id,row,grados)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_dict, f, allow_unicode=True, sort_keys=False)

print(f"Se generaron {len(datos)} archivos YAML en el folder '{output_dir}'")
