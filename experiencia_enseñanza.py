import pandas as pd
from datetime import datetime

def procesar_y_exportar_diferencias(ruta_csv_entrada, ruta_csv_salida):
    # Leer el CSV
    df = pd.read_csv(ruta_csv_entrada)

    # Convertir fecha a datetime
    df['fechaCon'] = pd.to_datetime(df['fechaCon'], format='%d/%m/%Y', errors='coerce')

    # Año actual
    año_actual = datetime.now().year

    # Calcular diferencia de años
    df['añosTEC'] = año_actual - df['fechaCon'].dt.year

    # Sumar con ensPriv
    df['añosTotal'] = df['añosTEC'] + df['ensPriv']

    # Años de enseñanza virtual
    df['añosVirtual'] = df['ensVirt']

    # Crear nuevo DataFrame con columnas deseadas
    df_salida = df[['codigo', 'añosTEC', 'añosTotal','añosVirtual']]

    # Guardar a un nuevo CSV
    df_salida.to_csv(ruta_csv_salida, index=False)
    
    print(f"Archivo guardado exitosamente en: {ruta_csv_salida}")

procesar_y_exportar_diferencias('datos.csv', 'experiencia_enseñanza.csv')