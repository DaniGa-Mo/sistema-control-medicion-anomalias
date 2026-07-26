"""
Generador de dataset sintético — Sistema de Control de Medición y Detección
de Anomalías de Consumo (sector sanitario, Gran Concepción).

Simula el tipo de datos que gestionaría un Analista de Datos y Control de
Medición: clientes, medidores, lecturas mensuales de consumo, reclamos y
auditorías a contratistas. No usa datos reales de ninguna empresa ni cliente.
"""

import numpy as np
import pandas as pd
from faker import Faker
from datetime import date
import random

D2025_INI = date(2025, 1, 1)
D2025_FIN = date(2025, 12, 15)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("es_CL")
Faker.seed(SEED)

OUT = "/home/claude/proyecto_medicion/data"

# ----------------------------------------------------------------------
# 1. DIM_CLIENTES
# ----------------------------------------------------------------------
N_CLIENTES = 1500
COMUNAS = ["Concepción", "Talcahuano", "Hualpén", "Chiguayante", "San Pedro de la Paz"]
COMUNA_PESOS = [0.32, 0.24, 0.14, 0.16, 0.14]
TIPO_CLIENTE = ["Residencial", "Comercial", "Industrial"]
TIPO_PESOS = [0.86, 0.11, 0.03]

clientes = pd.DataFrame({
    "id_cliente": [f"CL-{i:05d}" for i in range(1, N_CLIENTES + 1)],
    "nombre_cliente": [fake.name() for _ in range(N_CLIENTES)],
    "direccion": [fake.street_address() for _ in range(N_CLIENTES)],
    "comuna": np.random.choice(COMUNAS, N_CLIENTES, p=COMUNA_PESOS),
    "tipo_cliente": np.random.choice(TIPO_CLIENTE, N_CLIENTES, p=TIPO_PESOS),
    "fecha_alta_contrato": [fake.date_between(start_date="-15y", end_date="-1y") for _ in range(N_CLIENTES)],
})

# ----------------------------------------------------------------------
# 2. DIM_MEDIDORES  (1 medidor activo por cliente + algunos reemplazados)
# ----------------------------------------------------------------------
MARCAS = ["Elster", "Sensus", "Itron", "Zenner", "Actaris"]
DIAMETROS = [13, 15, 19, 25, 38]
DIAM_PESOS = [0.55, 0.25, 0.12, 0.06, 0.02]

medidores_rows = []
mid_counter = 1
for _, cli in clientes.iterrows():
    # antigüedad del medidor: entre 0 y 14 años
    antig_anios = np.random.randint(0, 15)
    fecha_instalacion = date(2025 - antig_anios, np.random.randint(1, 13), np.random.randint(1, 28))
    # No todos los medidores con antigüedad tienen registro de verificación
    # (refleja huecos reales de datos en sistemas de terreno)
    tiene_registro_verif = np.random.random() < 0.6 if antig_anios > 2 else False
    ultima_verif = fake.date_between(start_date="-6y", end_date="today") if tiene_registro_verif else None

    if antig_anios < 5:
        requiere_verif = False
    elif ultima_verif is None:
        requiere_verif = True  # nunca verificado y ya tiene 5+ años
    else:
        anios_desde_verif = (date(2025, 12, 31) - ultima_verif).days / 365.25
        requiere_verif = anios_desde_verif >= 5

    medidores_rows.append({
        "id_medidor": f"MD-{mid_counter:05d}",
        "id_cliente": cli["id_cliente"],
        "marca": np.random.choice(MARCAS),
        "diametro_mm": np.random.choice(DIAMETROS, p=DIAM_PESOS),
        "fecha_instalacion": fecha_instalacion,
        "antiguedad_anios": antig_anios,
        "fecha_ultima_verificacion_metrologica": ultima_verif,
        "requiere_verificacion": requiere_verif,
        "estado_medidor": "Activo",
    })
    mid_counter += 1

medidores = pd.DataFrame(medidores_rows)

# ----------------------------------------------------------------------
# 3. FACT_LECTURAS  (consumo mensual, 12 meses de 2025)
# ----------------------------------------------------------------------
MESES_2025 = pd.date_range("2025-01-01", "2025-12-01", freq="MS")

# Consumo base esperado (m3/mes) según tipo de cliente
CONSUMO_BASE = {"Residencial": 15, "Comercial": 45, "Industrial": 220}

# Asignar a cada medidor un "perfil de anomalía" para el año
PERFILES = ["Normal", "Medidor Detenido", "Submedicion", "Falla Metrologica"]
PERFIL_PESOS = [0.88, 0.045, 0.045, 0.03]

medidores["perfil_anomalia_2025"] = np.random.choice(PERFILES, len(medidores), p=PERFIL_PESOS)

lecturas_rows = []
lid = 1
for _, med in medidores.iterrows():
    cliente_tipo = clientes.loc[clientes["id_cliente"] == med["id_cliente"], "tipo_cliente"].values[0]
    base = CONSUMO_BASE[cliente_tipo] * np.random.uniform(0.75, 1.3)
    perfil = med["perfil_anomalia_2025"]

    lectura_acumulada = np.random.uniform(500, 5000)  # lectura inicial del medidor (m3 acumulados)

    # mes en que "empieza" la anomalía (si aplica), para que no sea todo el año
    mes_inicio_anomalia = np.random.randint(2, 10)

    for idx, mes in enumerate(MESES_2025):
        ruido = np.random.normal(0, base * 0.08)
        consumo = base + ruido

        tipo_anomalia_mes = "Normal"

        if perfil == "Medidor Detenido" and idx >= mes_inicio_anomalia:
            consumo = 0.0
            tipo_anomalia_mes = "Medidor Detenido"
        elif perfil == "Submedicion" and idx >= mes_inicio_anomalia:
            # cae progresivamente hasta ~20% del consumo esperado
            factor = max(0.2, 1 - 0.15 * (idx - mes_inicio_anomalia))
            consumo = base * factor
            tipo_anomalia_mes = "Submedicion"
        elif perfil == "Falla Metrologica" and idx >= mes_inicio_anomalia:
            # lecturas erráticas: picos y caídas inconsistentes
            consumo = base * np.random.choice([0.1, 3.5, 0.05, 2.8])
            tipo_anomalia_mes = "Falla Metrologica"

        consumo = max(consumo, 0)
        lectura_acumulada += consumo

        lecturas_rows.append({
            "id_lectura": f"LC-{lid:07d}",
            "id_medidor": med["id_medidor"],
            "fecha_lectura": mes.date(),
            "lectura_acumulada_m3": round(lectura_acumulada, 2),
            "consumo_m3": round(consumo, 2),
            "tipo_anomalia_real": tipo_anomalia_mes,  # etiqueta "verdadera" (para validar el modelo de detección)
        })
        lid += 1

lecturas = pd.DataFrame(lecturas_rows)

medidores = medidores.drop(columns=["perfil_anomalia_2025"])  # no exponer la etiqueta "solución" en la dim

# ----------------------------------------------------------------------
# 4. DIM_CONTRATISTAS
# ----------------------------------------------------------------------
contratistas = pd.DataFrame({
    "id_contratista": [f"CT-{i:02d}" for i in range(1, 11)],
    "nombre_empresa": [fake.company() for _ in range(10)],
    "especialidad": np.random.choice(
        ["Cambio de Medidores", "Verificación Metrológica", "Terreno General"], 10, p=[0.4, 0.3, 0.3]
    ),
    "fecha_inicio_contrato": [fake.date_between(start_date="-4y", end_date="-3m") for _ in range(10)],
})

# ----------------------------------------------------------------------
# 5. FACT_RECLAMOS
# ----------------------------------------------------------------------
N_RECLAMOS = 320
TIPOS_RECLAMO = [
    "Consumo Elevado", "Medidor Detenido", "Corte No Programado",
    "Error de Facturación", "Solicitud Cambio de Medidor", "Fuga Visible",
]
ESTADOS = ["Cerrado", "Cerrado", "Cerrado", "En Proceso", "Abierto"]

reclamos_rows = []
for i in range(1, N_RECLAMOS + 1):
    cli = clientes.sample(1).iloc[0]
    med = medidores[medidores["id_cliente"] == cli["id_cliente"]].iloc[0]
    fecha_reclamo = fake.date_between(start_date=D2025_INI, end_date=D2025_FIN)
    estado = np.random.choice(ESTADOS)
    dias_resolucion = None
    fecha_cierre = None
    if estado == "Cerrado":
        dias_resolucion = int(np.random.gamma(3, 3))  # sesgo hacia resoluciones rápidas, cola larga
        fecha_cierre = fecha_reclamo + pd.Timedelta(days=dias_resolucion)

    reclamos_rows.append({
        "id_reclamo": f"RC-{i:05d}",
        "id_cliente": cli["id_cliente"],
        "id_medidor": med["id_medidor"],
        "comuna": cli["comuna"],
        "tipo_reclamo": np.random.choice(TIPOS_RECLAMO),
        "fecha_reclamo": fecha_reclamo,
        "estado_reclamo": estado,
        "fecha_cierre": fecha_cierre,
        "dias_resolucion": dias_resolucion,
        "id_contratista_asignado": contratistas.sample(1).iloc[0]["id_contratista"],
    })

reclamos = pd.DataFrame(reclamos_rows)

# ----------------------------------------------------------------------
# 6. FACT_AUDITORIAS_TERRENO
# ----------------------------------------------------------------------
N_AUDITORIAS = 210
TIPOS_TRABAJO = ["Cambio de Medidor", "Verificación Metrológica", "Instalación Nueva", "Revisión por Reclamo"]

auditorias_rows = []
for i in range(1, N_AUDITORIAS + 1):
    ct = contratistas.sample(1).iloc[0]
    med = medidores.sample(1).iloc[0]
    cumple = np.random.choice([1, 0], p=[0.84, 0.16])
    auditorias_rows.append({
        "id_auditoria": f"AU-{i:04d}",
        "id_contratista": ct["id_contratista"],
        "id_medidor": med["id_medidor"],
        "fecha_auditoria": fake.date_between(start_date=D2025_INI, end_date=D2025_FIN),
        "tipo_trabajo": np.random.choice(TIPOS_TRABAJO),
        "cumple_estandar": cumple,
        "observaciones": "" if cumple else np.random.choice([
            "Documentación incompleta", "Precinto de seguridad faltante",
            "Medidor mal nivelado", "No se registró lectura inicial",
            "Plazo de ejecución excedido",
        ]),
    })

auditorias = pd.DataFrame(auditorias_rows)

# ----------------------------------------------------------------------
# GUARDAR CSVs
# ----------------------------------------------------------------------
import os
os.makedirs(OUT, exist_ok=True)

clientes.to_csv(f"{OUT}/dim_clientes.csv", index=False, encoding="utf-8-sig")
medidores.to_csv(f"{OUT}/dim_medidores.csv", index=False, encoding="utf-8-sig")
contratistas.to_csv(f"{OUT}/dim_contratistas.csv", index=False, encoding="utf-8-sig")
lecturas.to_csv(f"{OUT}/fact_lecturas.csv", index=False, encoding="utf-8-sig")
reclamos.to_csv(f"{OUT}/fact_reclamos.csv", index=False, encoding="utf-8-sig")
auditorias.to_csv(f"{OUT}/fact_auditorias.csv", index=False, encoding="utf-8-sig")

print("Filas generadas:")
print("  dim_clientes:", len(clientes))
print("  dim_medidores:", len(medidores))
print("  dim_contratistas:", len(contratistas))
print("  fact_lecturas:", len(lecturas))
print("  fact_reclamos:", len(reclamos))
print("  fact_auditorias:", len(auditorias))
print("\nDistribución tipo_anomalia_real en fact_lecturas:")
print(lecturas["tipo_anomalia_real"].value_counts())
