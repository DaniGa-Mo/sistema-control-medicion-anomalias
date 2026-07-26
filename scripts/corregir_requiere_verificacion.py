"""
Corrección puntual del bug en dim_medidores.csv (columna requiere_verificacion).

No regenera todo el dataset (para no alterar fact_lecturas y no invalidar
las métricas de detección ya calculadas/cargadas en Power BI) — solo
recalcula esta columna sobre el archivo ya existente, con la regla de
negocio correcta.
"""

import pandas as pd
from datetime import date

DATA = "/home/claude/proyecto_medicion/data"
FECHA_CORTE = date(2025, 12, 31)  # "hoy" dentro del dataset, fin de 2025

medidores = pd.read_csv(f"{DATA}/dim_medidores.csv", parse_dates=["fecha_ultima_verificacion_metrologica"])

def calcular_requiere_verificacion(row):
    if row["antiguedad_anios"] < 5:
        return False
    if pd.isna(row["fecha_ultima_verificacion_metrologica"]):
        return True  # nunca verificado y ya tiene 5+ años
    anios_desde_verif = (FECHA_CORTE - row["fecha_ultima_verificacion_metrologica"].date()).days / 365.25
    return anios_desde_verif >= 5  # verificado hace 5+ años

medidores["requiere_verificacion"] = medidores.apply(calcular_requiere_verificacion, axis=1)

medidores.to_csv(f"{DATA}/dim_medidores.csv", index=False, encoding="utf-8-sig")

print(medidores["requiere_verificacion"].value_counts())
