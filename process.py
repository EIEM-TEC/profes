import pandas as pd
import yaml
import os
from datetime import date

today = date.today()

# === Cargar los csv con los datos de los profes ===
datos = pd.read_csv("00_datos.csv")
grados = pd.read_csv("01_grados.csv")
experencia = pd.read_csv("02_experiencia_industria.csv")
idiomas = pd.read_csv("03_idiomas.csv")
areas = pd.read_csv("04_areas_interes.csv")
publicaciones = pd.read_csv("05_publicaciones.csv")
cursos = pd.read_csv("06_cursos.csv")
carrera = pd.read_csv("07_carrera.csv")
proyect = pd.read_csv("08_proyectos_inv_ext.csv")
habilil = pd.read_csv("09_habilidades.csv")
membres = pd.read_csv("10_membresias.csv")
                

# === Step 2: Create output folder ===
output_dir = "yamls"
os.makedirs(output_dir, exist_ok=True)

def make_education_entries(id,grados):
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

def make_career_entries(id,carrera):
    career_entries = []
    for _, row in carrera.iterrows():
        entry = {
            "name": row["categoria"],
            "date": row["fecha"],
        }
        career_entries.append(entry)
    return career_entries

def make_publication_entries(id,publicaciones):
    publication_entries = []
    for _, row in publicaciones.iterrows():
        autoresd = row.get("autores","").split(";")
        autores = [x.strip() for x in autoresd]
        entry = {
            "title": row["titulo"],
            "authors": autores
        }
        publication_entries.append(entry)
    return publication_entries

def make_rendercv_yaml(id,datos,grados):
    print(datos.nombre)
    match datos.titulo:
            case "M.Sc." | "Lic." | "Ing." | "Máster" | "Dr.-Ing." | "Mag.":
                nombre =  f"{datos.titulo} {datos.nombre}"
            case "Ph.D.":
                nombre = f"{datos.nombre}, {datos.titulo}"
    education = make_education_entries(id,grados[grados["codigo"]==id])
    career = make_career_entries(id,carrera[carrera["codigo"]==id])
    public = make_publication_entries(id,publicaciones[publicaciones["codigo"]==id])
    yaml_dict = {
        "cv": {
            "name": nombre,
            "email": datos["correo"],
            "phone": f"+506-{datos["telefono"]}",
            "sections": {
                "Información laboral": [
                    {
                        "label": "Cédula",
                        "details": str(datos["cedula"])
                    },
                    {
                        "label": "Tipo de nombramiento",
                        "details": datos["tipoNom"]
                    },
                    {
                        "label": "Fecha de contratación",
                        "details": datos["fechaCon"]
                    },
                    {
                        "label": "Sede",
                        "details": datos["sede"]
                    },
                    {
                        "label": "Escuela",
                        "details": datos["escuela"]
                    },
                    {
                        "label": "Correo",
                        "details": datos["correo"]
                    },
                    {
                        "label": "ORCID",
                        "details": datos["orcid"] if datos["orcid"] != "00" else "N/A"
                    }
                ],
                "Educación": education,
                "Carrera profesional": career,
                "Publicaciones": public,                
            },
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
            "abbreviations_for_months": {
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
            },
            "full_names_of_months": {
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
            }
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
                    "degree_column_width": "2.5cm"
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