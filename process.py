import pandas as pd
import yaml
import os

# === Step 1: Load the CSV ===
datos = pd.read_csv("datos.csv")  # Update path if necessary

# === Step 2: Create output folder ===
output_dir = "yamls"
os.makedirs(output_dir, exist_ok=True)

# === Step 3: Function to create a RenderCV-compatible YAML dict ===
def make_rendercv_yaml(profe):



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
    yaml_dict = {
        "cv": {
            "name": profe["nombre"],
            "email": profe["correo"],
            "phone": f"+506-{row["telefono"]}",
            "orcid": profe["orcid"],
            "sections": {
                "education": [
                    {
                        "institution": profe.get("colegio", ""),
                        "area": profe.get("titulo", ""),
                        "degree": profe.get("titulo", ""),
                        "location": profe.get("colegio", ""),
                        "start_date": normalizar_fecha(profe.get("incCol", "")),
                        "end_date": normalizar_fecha(profe.get("incCol", "")),
                        "highlights": []
                    }
                ],
                "experience": [
                    {
                        "company": profe.get("escuela", ""),
                        "position": profe.get("tipoNom", ""),
                        "area": "Docencia",
                        "location": profe.get("sede", ""),
                        "start_date": normalizar_fecha(profe.get("fechaCon", "")),
                        "end_date": "present",
                        "highlights": []
                    }
                ]
            },
        },

        "locale": {
            "language": "es",
            "phone_number_format": "national",
            "page_numbering_template": "NAME - Página PAGE_NUMBER de TOTAL_PAGES",
            "last_updated_date_template": "Última actualización el TODAY",
            "date_template": "MONTH_ABBREVIATION YEAR"
        },
        "rendercv_settings": {
            "date": "2025-06-08",
            "render_command": {
                "output_folder_name": "CVs",
                "pdf_path": f"CVs/{profe["codigo"]}.pdf",
                "typst_path": f"CVs/{profe["codigo"]}.typ",
                "html_path": f"CVs/{profe["codigo"]}.html",
                "markdown_path": f"CVs/{profe["codigo"]}.md",
                "dont_generate_html": True,
                "dont_generate_markdown": False,
                "dont_generate_png": False
            }
        },

        # "personal": {
        #     "name": name,
        #     "email": row["correo"],
        #     "phone": str(row["telefono"]),
        #     "orcid": row["orcid"]
        # },

        
        # "education": [
        #     {
        #         "degree": row["titulo"],
        #         "institution": row["colegio"],
        #         "year": row.get("incCol", "")
        #     }
        # ],
        # "experience": [
        #     {
        #         "title": row["tipoNom"],
        #         "institution": row["escuela"],
        #         "location": row["sede"],
        #         "start_date": row["fechaCon"]
        #     }
        # ]
    }

    return yaml_dict, f"{profe["codigo"]}.yml"

# === Step 4: Generate YAML files for all employees ===
for _, row in datos.iterrows():
    yaml_dict, filename = make_rendercv_yaml(row)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_dict, f, allow_unicode=True, sort_keys=False)

print(f"✅ Se generaron {len(datos)} archivos YAML en el folder '{output_dir}'")





# import subprocess
# import pandas as pd


# datos = pd.read_csv("datos.csv")

# CVdir = "C:\\Repositories\\profes\\datos\\"
# name = "JRH0"

# print(datos)

# def generate_rendercv_yaml(codigo):
    
#     data = {
#         "name": codigo["name"],
#         "email": codigo["email"],
#         "phone": codigo["phone"],
#         "education": codigo["education"],
#         "experience": codigo["experience"]
#     }
#     generate_rendercv_yaml




# for _, row in df.iterrows():
#     emp = {
#         "name": row["Name"],
#         "email": row["Email"],
#         "phone": row["Phone"],
#         "education": eval(row["Education"]),     # assuming education is a stringified list of dicts
#         "experience": eval(row["Experience"])    # same here
#     }
#     generate_rendercv_yaml(emp)



#subprocess.run(f"rendercv render {CVdir}{name}_CV.yaml", shell=True, check=True)
