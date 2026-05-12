# Clasificacion de profesores por saberes

Script:

```powershell
python clasificacion_saberes/clasificar_profes_saberes.py
```

Por defecto usa las secciones `educacion` y `publicaciones` de los CVs. La
educacion se toma de `01_grados.csv`; las publicaciones usan solo el campo
`titulo` de `06_publicaciones.csv`, no el nombre de la revista. Esos textos se
comparan contra:

- `rasgos_ejes/saberes.csv`
- `cursos/cursos_rasgos.csv`
- `areas.csv`
- `cursos/plan_de_estudios.csv`

Los CSV de CLIE se guardan en `clasificacion_saberes/data/`.

## Outputs

Los resultados se guardan en `clasificacion_saberes/output/`:

- `personas_saberes.csv`: tabla detallada persona-saber con puntaje, fuentes y evidencia textual.
- `personas_saberes_resumen.csv`: resumen por persona.
- `personas_cursos.csv`: cursos que la persona puede impartir si cubre todos los saberes requeridos del curso.
- `personas_cursos_resumen.csv`: resumen de cursos por persona.

## Opciones utiles

Actualizar los CSV desde GitHub:

```powershell
python clasificacion_saberes/clasificar_profes_saberes.py --refresh
```

Usar mas evidencia del CV, ademas de estudios y titulos de articulos:

```powershell
python clasificacion_saberes/clasificar_profes_saberes.py --sections educacion,areas_interes,cursos_impartidos,experiencia,publicaciones,proyectos
```

Volver al criterio de solo estudios:

```powershell
python clasificacion_saberes/clasificar_profes_saberes.py --sections educacion
```

Ajustar criterios:

```powershell
python clasificacion_saberes/clasificar_profes_saberes.py --min-saber-score 5 --min-course-coverage 1.0
```

`--min-course-coverage 1.0` exige cubrir todos los saberes del curso.

## Graficos por persona

Generar un PDF con un grafico de pastel por persona. Cada segmento es un saber
y el tamano del segmento se calcula con el `score` de `personas_saberes.csv`.

```powershell
python clasificacion_saberes/graficar_personas_saberes.py
```

El PDF se guarda en `clasificacion_saberes/output/personas_saberes_graficos.pdf`.
