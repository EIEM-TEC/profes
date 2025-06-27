import pandas as pd
import yaml
import os
from datetime import date, datetime
import rendercv.data.generator as gen

model = gen.create_a_sample_data_model(name="juanjo", theme="engineeringresumes")

# Convert to plain dict using Pydantic (no __dict__, no !!python/object, etc.)
clean_dict = model.model_dump()  # Use .dict() if you're using older pydantic

# Dump as normal YAML
with open("example.yaml", 'w', encoding='utf-8') as f:
    yaml.dump(clean_dict, f, allow_unicode=True, sort_keys=False)

today = date.today()

# === Cargar los csv con los datos de los profes ===
datos = pd.read_csv("00_datos.csv")
grados = pd.read_csv("01_grados.csv")
experi = pd.read_csv("02_experiencia_industria.csv")
experi.fillna("",inplace=True)
idiomas = pd.read_csv("03_idiomas.csv")
areas = pd.read_csv("04_areas_interes.csv")
cursos = pd.read_csv("05_cursos.csv")
publicaciones = pd.read_csv("06_publicaciones.csv")
publicaciones.fillna("0",inplace=True)
carrera = pd.read_csv("07_carrera.csv")
proyect = pd.read_csv("08_proyectos_inv_ext.csv")
proyect["codigo"] = proyect["codigo"].str.split(";",expand=False)
proyect = proyect.explode("codigo")
habilil = pd.read_csv("09_habilidades.csv")
membres = pd.read_csv("10_membresias.csv")
                

# === Step 2: Create output folder ===
output_dir = "yamls"
os.makedirs(output_dir, exist_ok=True)

def convert_cr_to_iso(date_cr):
    if date_cr != "present":
        return datetime.strptime(date_cr, "%d/%m/%Y").strftime("%Y-%m-%d")
    else:
        return date_cr

def make_education_entries(grados):
    education_entries = []
    for _, row in grados.iterrows():
        entry = {
            "institution": row["institucion"],
            "area": row["campo"],
            "degree": row["grado"],
            "location": row["pais"],
            "end_date": f"{int(row['año'])}",
        }
        education_entries.append(entry)
    return education_entries

def make_career_entries(carrera):
    career_entries = []
    for _, row in carrera.iterrows():
        entry = {
            "name": row["categoria"],
            "date": row["fecha"],
        }
        career_entries.append(entry)
    return career_entries

def make_publication_entries(publicaciones):
    publication_entries = []
    for _, row in publicaciones.iterrows():
        autoresd = row.get("autores","").split(";")
        autores = [x.strip() for x in autoresd]
        date = f"{int(row["dia"]):02d}/{int(row["mes"]):02d}/{int(row["año"])}"
        if row["dia"] == "0": 
            date = f"{int(row["mes"])}/{int(row["año"])}"
        if row["mes"] == "0":
            date = f"{int(row["año"])}"
        entry = {
            "title": row["titulo"],
            "journal": row["revista"],
            "authors": autores,
            "date": date,
            "doi": row["doi"]
        }
        publication_entries.append(entry)
    return publication_entries

def make_courses_entries(cursos):
    courses_entries = []
    for _, row in cursos.iterrows():
        entry = {
            "bullet": f"{row["codCurso"]} - {row["curso"]}"
        }
        courses_entries.append(entry)
    return courses_entries

def make_research_entries(proyect):
    research_entries = []
    for _, row in proyect.iterrows():
        entry = {
            "name": row["proyecto"],
            "start_date": convert_cr_to_iso(row["inicio"]),
            "end_date": convert_cr_to_iso(row["fin"]),
            "highlights": [
                f"**Numero:** {row["numProy"]}",
                f"**Tipo:** {row["tipo"]}",
                f"**Escuela:** {row["nombre"]}"    
            ]        
        }
        research_entries.append(entry)
    return research_entries

def make_experience_entries(experi):
    experi_entries = []
    for _, row in experi.iterrows():
        entry = {
            "company": row["empresa"],
            "position": row["puesto"],
            "start_date": convert_cr_to_iso(row["inicio"]),
            "end_date": convert_cr_to_iso(row["fin"]),
            "summary": row["descripcion"]
        }
        experi_entries.append(entry)
    return experi_entries  

def make_language_entries(idiomas):
    idiom_entries = []
    for _, row in idiomas.iterrows():
        entry = {
            "bullet": f"{row["idioma"]}: {row["detalle"]}"
        }
        idiom_entries.append(entry)
    return idiom_entries  

def make_interest_entries(areas):
    area_entries = []
    for _, row in areas.iterrows():
        entry = {
            "bullet": f"{row["area"]}"
        }
        area_entries.append(entry)
    return area_entries 

def make_rendercv_yaml(id,datos,grados):
    print(datos.nombre)
    match datos.titulo:
            case "M.Sc." | "Lic." | "Ing." | "Máster" | "Dr.-Ing." | "Mag.":
                nombre =  f"{datos.titulo} {datos.nombre}"
            case "Ph.D.":
                nombre = f"{datos.nombre}, {datos.titulo}"
    education = make_education_entries(grados[grados["codigo"]==id])
    career = make_career_entries(carrera[carrera["codigo"]==id])
    public = make_publication_entries(publicaciones[publicaciones["codigo"]==id])
    research = make_research_entries(proyect[proyect["codigo"]==id])
    experie = make_experience_entries(experi[experi["codigo"]==id])
    languag = make_language_entries(idiomas[idiomas["codigo"]==id])
    interes = make_interest_entries(areas[areas["codigo"]==id])
    cursoss = make_courses_entries(cursos[cursos["codigo"]==id])
    sections = {
    "Información laboral": [
        {"label": "Cédula", "details": str(datos["cedula"])},
        {"label": "Tipo de nombramiento", "details": datos["tipoNom"]},
        {"label": "Fecha de contratación", "details": datos["fechaCon"]},
        {"label": "Sede", "details": datos["sede"]},
        {"label": "Escuela", "details": datos["escuela"]},
        {"label": "Correo", "details": datos["correo"]},
        {"label": "ORCID", "details": datos["orcid"] if datos["orcid"] != "00" else "N/A"},
    ]
    }
    sections["Educación"] = education
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

    yaml_dict = {
        "cv": {
            "name": nombre,
            "email": datos["correo"],
            "phone": f"+506-{datos["telefono"]}",
            "sections": sections,         
        },
        "locale": {
            "language": "es",
            "phone_number_format": "national",
            "page_numbering_template": "NAME - Página PAGE_NUMBER de TOTAL_PAGES",
            "last_updated_date_template": f"Última actualización: {today.strftime("%d/%m/%Y")}",
            "date_template": "MONTH_ABBREVIATION YEAR",
            "month": "mes",
            "months": "meses",
            "year": "año",
            "years": "años",
            "present": "actualmente",
            "to": "-",
            "abbreviations_for_months": [
                "Ene",
                "Feb",
                "Mar",
                "Abr",
                "May",
                "Jun",
                "Jul",
                "Ago",
                "Sep",
                "Oct",
                "Nov",
                "Dic"
            ],
            "full_names_of_months": [
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
                "Octubre",
                "Noviembre",
                "Diciembre",
            ]
        },
        "rendercv_settings": {
            "date": "2025-06-08",
            "render_command": {
                "output_folder_name": "CVs",
                "dont_generate_html": True,
                "dont_generate_markdown": True,
                "dont_generate_png": True
            }
        },
        "design": {
            "theme": "engineeringresumes", 
            "entry_types": {
                "education_entry": {
                    "main_column_first_row_template": '**INSTITUTION**, DEGREE en AREA',
                    "degree_column_width": "2.5cm"
                },
                "experience_entry": {
                    "date_and_location_column_template": "DATE"
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

print(f"✅ Se generaron {len(datos)} archivos YAML en el folder '{output_dir}'")