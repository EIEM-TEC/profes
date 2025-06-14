import pandas as pd

datos = pd.read_csv("00_datos.csv")
grados = pd.read_csv("01_grados.csv")
publicaciones = pd.read_csv("05_publicaciones.csv")
carrera = pd.read_csv("07_carrera.csv")

tabla = datos[["nombre","cedula","correo"]]
tabla[""]

print(tabla)
