import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
YAML_DIR = ROOT_DIR / "yamls"
CV_DIR = ROOT_DIR / "CVs"

datos = pd.read_csv(ROOT_DIR / "00_datos.csv")

# datos = pd.read_csv(ROOT_DIR / "datos.csv")

for _, row in datos.iterrows():
    print(f"{row.nombre} ({row.codigo})")
    id = row["codigo"]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rendercv",
            "render",
            str(YAML_DIR / f"{id}.yml"),
            "--quiet",
        ],
        check=True,
    )

for typ_file in CV_DIR.glob("*.typ"):
    typ_file.unlink()
