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
    yaml_dict = {
        "cv": {
            "name": profe["nombre"],
            "email": profe["correo"],
            "phone": f"+506-{row["telefono"]}",
            "orcid": profe["orcid"]
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
        }
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