import pandas as pd
from datetime import datetime

today = pd.to_datetime(datetime.today().date())

datos = pd.read_csv("00_datos.csv")
grados = pd.read_csv("01_grados.csv")
publicaciones = pd.read_csv("05_publicaciones.csv")
proyectos = pd.read_csv("08_proyectos_inv_ext.csv")
carrera = pd.read_csv("07_carrera.csv")


tabla = datos[["codigo","nombre","cedula","correo","fechaCon"]].copy()
tabla["orden"] = tabla["codigo"].str.slice(1,3)
tabla = tabla.sort_values(by="orden").drop(columns="orden").reset_index(drop=True)

jerarquia = {
    "Especialización": 1,
    "Bachillerato": 2,
    "Licenciatura": 3,
    "Maestría": 4,
    "Doctorado": 5
}

grados["jerarquia"] = grados["grado"].map(jerarquia)
df_max = grados.loc[grados.groupby("codigo")["jerarquia"].idxmax()]
tabla["grado"] = tabla["codigo"].map(df_max.set_index("codigo")["grado"])

tabla["fechaCon"] = pd.to_datetime(tabla["fechaCon"], format="%d/%m/%Y")
tabla["expUniv"] = (today - tabla["fechaCon"]).dt.days // 365
tabla.drop(columns="fechaCon",inplace=True)

publicaciones["año"] = pd.to_numeric(publicaciones["año"], errors="coerce")
publicacionsU5A = publicaciones[publicaciones["año"] >= (datetime.now().year - 5)]
pubpp = publicacionsU5A["codigo"].value_counts().reset_index()
pubpp.columns = ["codigo", "pub5a"]

tabla = tabla.merge(pubpp, on="codigo", how="left")
tabla["pub5a"] = tabla["pub5a"].fillna(0).astype(int)

proyectos["codigo"] = proyectos["codigo"].str.split(";",expand=False)
proyectos = proyectos.explode("codigo")
proyectos["fin"] = pd.to_datetime(proyectos["fin"], format="%m/%d/%Y", errors="coerce")
proyectosU5A = proyectos[proyectos["fin"].dt.year >= (datetime.now().year - 5)]
propp = proyectosU5A["codigo"].value_counts().reset_index()
propp.columns = ["codigo", "pro5a"]

tabla = tabla.merge(propp, on="codigo", how="left")
tabla["pro5a"] = tabla["pro5a"].fillna(0).astype(int)

tabla.to_csv('tabla.csv',index=False)