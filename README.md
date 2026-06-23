# Programa para generar curriculums vitae para los profesores de la Escuela de Ingeniería Electromecánica

## Requisitos

Este proyecto usa un archivo `requirements.txt`, que es la convención más común en proyectos de Python para listar dependencias.

Para instalar todo en un ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Uso

1. Verificar que los CSV locales de CLIE coinciden con sus fuentes oficiales:

```powershell
python verificar_plan_de_estudios.py
```

El script compara `plan_de_estudios.csv`, `cursos_rasgos.csv`, `areas.csv` y
`saberes.csv` dentro de `clasificacion_saberes/data/` contra el repositorio
oficial `EIEM-TEC/CLIE`.

2. Generar los archivos YAML:

```powershell
python process.py
```

3. Crear los CVs con RenderCV:

```powershell
python .\yamls\0_create_CVs.py
```

4. Fusionar PDFs generados:

```powershell
python .\CVs\0fusionar.py
```

## Autor
Juan J. Rojas. 
Escuela de Ingeniería Electromecánica
Instituto Tecnológico de Costa Rica
