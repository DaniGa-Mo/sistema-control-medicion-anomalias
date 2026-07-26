"""
Motor de detección de anomalías de consumo.

Aplica reglas de negocio típicas de control de medición sobre las lecturas
mensuales, y valida el desempeño contra la etiqueta "real" simulada
(tipo_anomalia_real) para reportar precisión del modelo — un argumento
fuerte de portafolio: "detecté anomalías con X% de precisión sobre
18.000 lecturas".

Reglas implementadas:
  1. Medidor Detenido   -> 2+ meses consecutivos con consumo = 0
  2. Submedición        -> caída sostenida (>=3 meses) por debajo del 60%
                           del promedio histórico del propio medidor
  3. Falla Metrológica  -> coeficiente de variación mensual anormalmente alto
                           (lecturas erráticas, picos y caídas bruscas)
  4. Consumo Elevado    -> mes puntual > 2.5x el promedio histórico del medidor
"""

import pandas as pd
import numpy as np

DATA = "/home/claude/proyecto_medicion/data"

lecturas = pd.read_csv(f"{DATA}/fact_lecturas.csv", parse_dates=["fecha_lectura"])
lecturas = lecturas.sort_values(["id_medidor", "fecha_lectura"]).reset_index(drop=True)

resultados = []

for medidor, grupo in lecturas.groupby("id_medidor"):
    grupo = grupo.sort_values("fecha_lectura").reset_index(drop=True)
    consumo = grupo["consumo_m3"].values
    promedio_hist = consumo.mean()
    std_hist = consumo.std()

    detecciones = ["Normal"] * len(grupo)

    # --- Regla 1: Medidor Detenido (2+ meses consecutivos en 0) ---
    ceros = consumo == 0
    racha = 0
    for i in range(len(consumo)):
        racha = racha + 1 if ceros[i] else 0
        if racha >= 2:
            detecciones[i] = "Medidor Detenido"
            detecciones[i - 1] = "Medidor Detenido"

    # --- Regla 2: Submedición (caída sostenida >=3 meses bajo 60% del promedio) ---
    umbral_bajo = promedio_hist * 0.6
    racha_baja = 0
    for i in range(len(consumo)):
        if detecciones[i] != "Normal":
            continue
        if 0 < consumo[i] < umbral_bajo:
            racha_baja += 1
        else:
            racha_baja = 0
        if racha_baja >= 3:
            detecciones[i] = "Submedicion"
            detecciones[i - 1] = "Submedicion" if detecciones[i - 1] == "Normal" else detecciones[i - 1]
            detecciones[i - 2] = "Submedicion" if detecciones[i - 2] == "Normal" else detecciones[i - 2]

    # --- Regla 3: Falla Metrológica (variación brusca mes a mes) ---
    if std_hist > 0:
        for i in range(1, len(consumo)):
            if detecciones[i] != "Normal":
                continue
            variacion = abs(consumo[i] - consumo[i - 1]) / (promedio_hist + 1e-6)
            if variacion > 1.5:  # salto o caída de más del 150% respecto al mes anterior
                detecciones[i] = "Falla Metrologica"

    # --- Regla 4: Consumo Elevado puntual ---
    for i in range(len(consumo)):
        if detecciones[i] != "Normal":
            continue
        if consumo[i] > promedio_hist * 2.5 and promedio_hist > 0:
            detecciones[i] = "Consumo Elevado"

    grupo["tipo_anomalia_detectada"] = detecciones
    resultados.append(grupo)

lecturas_final = pd.concat(resultados, ignore_index=True)
lecturas_final.to_csv(f"{DATA}/fact_lecturas_anomalias_detectadas.csv", index=False, encoding="utf-8-sig")

# ----------------------------------------------------------------------
# Evaluación del modelo (agrupando por categoría "hay anomalía" sí/no,
# y también por tipo específico)
# ----------------------------------------------------------------------
real = lecturas_final["tipo_anomalia_real"]
detectada = lecturas_final["tipo_anomalia_detectada"]

real_bin = real != "Normal"
det_bin = detectada != "Normal"

TP = ((real_bin) & (det_bin)).sum()
FP = ((~real_bin) & (det_bin)).sum()
FN = ((real_bin) & (~det_bin)).sum()
TN = ((~real_bin) & (~det_bin)).sum()

precision = TP / (TP + FP) if (TP + FP) else 0
recall = TP / (TP + FN) if (TP + FN) else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

print("=== Evaluación detección binaria (anomalía vs normal) ===")
print(f"TP={TP}  FP={FP}  FN={FN}  TN={TN}")
print(f"Precisión: {precision:.1%}")
print(f"Recall:    {recall:.1%}")
print(f"F1-score:  {f1:.1%}")

print("\n=== Matriz de confusión por tipo específico ===")
print(pd.crosstab(real, detectada, rownames=["Real"], colnames=["Detectada"]))

print("\n=== Resumen de anomalías detectadas ===")
print(detectada.value_counts())

# Guardar métricas para el README / dashboard
metricas = pd.DataFrame([{
    "TP": TP, "FP": FP, "FN": FN, "TN": TN,
    "precision": round(precision, 4),
    "recall": round(recall, 4),
    "f1_score": round(f1, 4),
    "total_lecturas": len(lecturas_final),
    "total_anomalias_detectadas": int(det_bin.sum()),
}])
metricas.to_csv(f"{DATA}/metricas_deteccion.csv", index=False)
