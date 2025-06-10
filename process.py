import pandas as pd
import yaml
import os
from datetime import date

today = date.today()

# === Cargar los csv con los datos de los profes ===
datos = pd.read_csv("datos.csv")
grados = pd.read_csv("grados.csv")
carrera = pd.read_csv("carrera.csv")
publicacioness = pd.read_csv("publicaciones.csv")

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
            "end_date": f"{int(row['año'])}-{int(row.get("mes","01")):02}",
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

def make_publication_entries(id,publicaciones)

# Normalizar fecha (si viene como dd/mm/yyyy)
def normalizar_fecha(fecha, permitir_año=True):
    try:
        if isinstance(fecha, float):
            return str(int(fecha))
        if "/" in fecha:
            partes = fecha.strip().split("/")
            if len(partes) == 3:
                return f"{partes[2]}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
            elif len(partes) == 2:
                return f"{partes[1]}-{partes[0].zfill(2)}"
            elif len(partes) == 1:
                return partes[0] if permitir_año else ""
        if "-" in fecha:
            return fecha  # ya tiene formato válido
        if len(fecha) == 4 and fecha.isdigit():
            return fecha
    except:
        pass
    return

# === Step 3: Function to create a RenderCV-compatible YAML dict ===
def make_rendercv_yaml(id,datos,grados):
    education = make_education_entries(id,grados[grados["codigo"]==id])
    career = make_career_entries(id,carrera[carrera["codigo"]==id])
    yaml_dict = {
        "cv": {
            "name": datos["nombre"],
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
                        "details": datos["orcid"]
                    }
                ],
                "Educación": education,
                "Carrera profesional": career,                
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
                "pdf_path": f"CVs/{id}.pdf",
                "typst_path": f"CVs/{id}.typ",
                "html_path": f"CVs/{id}.html",
                "markdown_path": f"CVs/{id}.md",
                "dont_generate_html": True,
                "dont_generate_markdown": False,
                "dont_generate_png": False
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