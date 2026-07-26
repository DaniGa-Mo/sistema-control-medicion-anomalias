# Medidas DAX sugeridas — Dashboard Power BI

Copia y pega estas medidas en Power BI (pestaña "Modelado" → "Nueva medida").
Están pensadas para las 4 páginas del dashboard.

## Página 1 — Resumen Ejecutivo

```DAX
Total Consumo m3 = SUM(fact_lecturas_anomalias_detectadas[consumo_m3])

Total Medidores Activos = DISTINCTCOUNT(dim_medidores[id_medidor])

Total Anomalias Detectadas =
CALCULATE(
    COUNTROWS(fact_lecturas_anomalias_detectadas),
    fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] <> "Normal"
)

% Medidores con Anomalia =
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(fact_lecturas_anomalias_detectadas[id_medidor]),
        fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] <> "Normal"
    ),
    [Total Medidores Activos]
)

Reclamos Abiertos =
CALCULATE(COUNTROWS(fact_reclamos), fact_reclamos[estado_reclamo] = "Abierto")

Reclamos En Proceso =
CALCULATE(COUNTROWS(fact_reclamos), fact_reclamos[estado_reclamo] = "En Proceso")

Dias Promedio Resolucion Reclamo =
AVERAGE(fact_reclamos[dias_resolucion])
```

## Página 2 — Detección de Anomalías

```DAX
Medidores Detenidos =
CALCULATE(
    DISTINCTCOUNT(fact_lecturas_anomalias_detectadas[id_medidor]),
    fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] = "Medidor Detenido"
)

Casos Submedicion =
CALCULATE(
    DISTINCTCOUNT(fact_lecturas_anomalias_detectadas[id_medidor]),
    fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] = "Submedicion"
)

Casos Falla Metrologica =
CALCULATE(
    DISTINCTCOUNT(fact_lecturas_anomalias_detectadas[id_medidor]),
    fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] = "Falla Metrologica"
)

% Precision Modelo (usar solo si incluyes la etiqueta real como contexto histórico) =
VAR TP = CALCULATE(COUNTROWS(fact_lecturas_anomalias_detectadas),
            fact_lecturas_anomalias_detectadas[tipo_anomalia_real] <> "Normal",
            fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] <> "Normal")
VAR TotalDetectadas = CALCULATE(COUNTROWS(fact_lecturas_anomalias_detectadas),
            fact_lecturas_anomalias_detectadas[tipo_anomalia_detectada] <> "Normal")
RETURN DIVIDE(TP, TotalDetectadas)
```

**Visuales sugeridos:** matriz de calor (comuna x tipo de anomalía), gráfico
de barras (conteo por `tipo_anomalia_detectada`), tabla detallada con
segmentación por comuna/tipo de cliente, tarjeta con % precisión del modelo.

## Página 3 — Gestión de Medidores

```DAX
Medidores Requieren Verificacion =
CALCULATE(COUNTROWS(dim_medidores), dim_medidores[requiere_verificacion] = TRUE)

Antiguedad Promedio Medidores =
AVERAGE(dim_medidores[antiguedad_anios])

Medidores +10 años =
CALCULATE(COUNTROWS(dim_medidores), dim_medidores[antiguedad_anios] >= 10)
```

**Visuales sugeridos:** histograma de antigüedad, tabla de medidores
priorizados para cambio (antigüedad alta + anomalía activa + sin
verificación), mapa o barras por comuna.

## Página 4 — Desempeño de Contratistas

```DAX
% Cumplimiento Auditorias =
DIVIDE(
    CALCULATE(COUNTROWS(fact_auditorias), fact_auditorias[cumple_estandar] = 1),
    COUNTROWS(fact_auditorias)
)

Reclamos por Contratista =
COUNTROWS(fact_reclamos)  -- usar en tabla agrupada por id_contratista_asignado

Auditorias Realizadas = COUNTROWS(fact_auditorias)
```

**Visuales sugeridos:** ranking de contratistas por % cumplimiento, tabla de
observaciones más frecuentes en auditorías no conformes, tendencia mensual
de auditorías realizadas vs. programadas.

## Tabla de Calendario (crear en Power BI)

```DAX
Calendario =
CALENDAR(DATE(2025,1,1), DATE(2025,12,31))
```
Relacionar con `fecha_lectura`, `fecha_reclamo` y `fecha_auditoria` para
habilitar segmentaciones de fecha unificadas y Time Intelligence.
