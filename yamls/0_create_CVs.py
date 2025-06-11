import subprocess
import pandas as pd
datos = pd.read_csv("datos.csv")

# datos = pd.read_csv("datos.csv")

CVdir = "C:\\Repositories\\profes\\yamls\\"
name = "JRH0"

subprocess.run(f"rendercv render {CVdir}{name}.yml", shell=True, check=True)

# for _, row in datos.iterrows():
#     id = row["codigo"]
#     subprocess.run(f"rendercv render {CVdir}{id}.yml", shell=True, check=True)