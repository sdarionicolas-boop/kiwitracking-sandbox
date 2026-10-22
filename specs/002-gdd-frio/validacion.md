# Validación — Spec 002

Fecha de la corrida: 22/10/2026. Comando: `.venv\Scripts\python -m pytest -W error -rs` → **793 tests, 793 pasan, 0 avisos, 0 saltados** (404 de la spec 001 y 389 de la spec 002).

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`; cuenta cada caso de los tests parametrizados). Los números salen de los nombres de los tests, no de una lectura semántica.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 16 | OK | test_clima_entrada, test_clima | Columnas obligatorias y tabla vacía |
| 2 | 33 | OK | test_clima_entrada | Fecha `AAAA-MM-DD` con o sin hora y zona, `formato_fecha` explícito, sin inferir, fechas vacías o ilegibles |
| 3 | 9 | OK | test_clima_entrada | Temperaturas no numéricas: error que nombra la columna |
| 4 | 13 | OK | test_clima_entrada | Fechas repetidas iguales (`FECHA_DUPLICADA`) o en conflicto (error con hasta 10 fechas) |
| 5 | 7 | OK | test_clima_entrada | `Tmax < Tmin`: error con la cantidad y las primeras 10 fechas |
| 6 | 10 | OK | test_clima_entrada | Temperaturas fuera de `rango_fisico` |
| 7 | 5 | OK | test_clima_entrada | Día con temperatura vacía = día faltante |
| 8 | 4 | OK | test_clima_entrada | El resultado no depende del orden de las filas |
| 9 | 81 | OK | test_clima_parametros | Cada valor no permitido da error con los permitidos; en modo "invierno", `meses_frio` solo continuo dentro del año |
| 10 | 7 | OK | test_clima_calculo | `GDD_diario = max(Tmedia − tbase, 0)` |
| 11 | 23 | OK | test_clima_calculo | Horas de frío con modelo de coseno: 24 si `Tmax ≤ umbral`, 0 si `Tmin ≥ umbral`, máscara de faltantes |
| 12 | 8 | OK | test_clima_periodos | Temporada desde el día 1 de `mes_inicio_temporada`, etiquetada por el año de inicio |
| 13 | 10 | OK | test_clima_periodos | Ventana "invierno" (año calendario) y "temporada" |
| 14 | 11 | OK | test_clima_periodos | Días disponibles y esperados, cobertura, hueco máximo (los días fuera del rango cuentan como faltantes) |
| 15 | 15 | OK | test_clima_periodos | `completo` = cobertura ≥ mínima y hueco ≤ límite (o `None`); bordes |
| 16 | 2 | OK | test_clima_periodos | Período sin datos no aparece |
| 17 | 13 | OK | test_clima | `GDD_total` por temporada, también si es incompleta |
| 18 | 7 | OK | test_clima | `PERIODO_INCOMPLETO` en GDD |
| 19 | 9 | OK | test_clima | `Horas_Frio` por ventana |
| 20 | 14 | OK | test_clima | `estado_frio` solo en ventanas completas; umbrales 950 y 750 |
| 21 | 2 | OK | test_clima | `COBERTURA_PARCIAL` |
| 22 | 14 | OK | test_campana, test_clima_integracion | Estado de la última campaña, utilizable en `analizar()` |
| 23 | 15 | OK | test_campana | `campana` enlaza con el período de igual etiqueta; error si no existe o no es clasificable |
| 24 | 5 | OK | test_campana, test_clima_integracion | Sin ventana clasificable: estado vacío y `SIN_PERIODO_CLASIFICABLE` |
| 25 | 4 | OK | test_campana | `COBERTURA_PARCIAL` en la ventana elegida |
| 26 | 4 | OK | test_clima | Tablas y advertencias, con las de entrada primero y luego por período |
| 27 | 5 | OK | test_clima | Modo de reproducción contra una copia independiente del cálculo del notebook; contra los datos reales: ver criterio 2 |
| 28 | 2 | OK | test_campana | `CAMPANA_NO_INDICADA` |

**Ninguno de los 28 RF queda sin test.** Los más delgados son RF-16, RF-21 y RF-28 (2 tests cada uno); alcanzan para su comportamiento. Los tests de datos reales (`test_clima_golden`, `test_clima_invierno`, `test_clima_campana_real`, `test_clima_procedencia`, 35 en total) llevan `criterioN` o `t20` en el nombre, no un número de RF.

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests `RF-n` pasan, con avisos como errores | **Cumplido** | 793/793 con `-W error` |
| 2 | Reproduce el notebook (GDD < 1e-9; horas 1e-6) | **Cumplido** | `test_clima_golden`: 8 temporadas; GDD total 14.445,325; los dos "Deficiente" de 2018 y 2025 salen de ventanas truncadas de ~50 % de cobertura |
| 3 | Horas del invierno por defecto (tolerancia 0,05 h) | **Cumplido** | `test_clima_invierno`: 956,5 / 853,5 / 925,0 / 1.090,4 / 853,5 / 1.128,8 / 834,2 |
| 4 | Estados por invierno, ninguno "Deficiente" | **Cumplido** | `test_clima_invierno` |
| 5 | Última campaña: 2025 "Adecuado" (0,9675, hueco 4, `CAMPANA_NO_INDICADA`); `campana=2024` "Óptimo" | **Cumplido** | `test_clima_campana_real` |
| 6 | GDD: 2019–2021, 2023, 2024 completas; 2022 (hueco 34), 2018 y 2025 incompletas | **Cumplido** | `test_clima_campana_real`; cobertura 2018 = 0,496, 2022 = 0,901, 2025 = 0,742 |
| 7 | Estado de la spec 002 en `analizar()`: 16 "Mantener" y 19 "Intervenir" | **Cumplido** | `test_clima_campana_real`, con `campana=None` y `2024` |
| 8 | Cada RF tiene al menos un test | **Cumplido** | Sección 1 (28 RF) |

## 3. Mutaciones

Cada cambio se aplicó con un script que verifica que el patrón existe, se corrió la suite completa y se restauró el código.

| Mutación | Resultado |
|---|---|
| Borde de cobertura `>=` → `>` | Detectada (1 test falla) |
| Borde del hueco `<=` → `<` | Detectada |
| Valor por defecto de `ventana_frio` ("invierno" → "temporada") | Detectada |
| Valor por defecto de `max_hueco_dias` (7 → `None`) | Detectada |
| `formato_fecha` ignorado al leer fechas | Detectada (4 tests fallan) |

En T2.0 a T2.18 se hicieron además mutaciones por tarea (cálculo diario, etiquetas de temporada, umbrales de estado, elección de campaña, reglas de completitud). Dos sobrevivieron y son equivalentes: `Tmin >= umbral` → `>` (la fórmula del coseno da 0 justo en el borde) y `iloc[0]` → `iloc[-1]` al elegir la fila de una campaña (hay una sola fila).

## 4. Limitaciones y dudas abiertas

- **Procedencia del clima.** 58 de los 2.604 días de `clima_diario.csv` no están verificados contra INTA (que los tiene vacíos; 243 más se confirmaron con una descarga posterior el 22/10/2026), y el invierno 2024 depende de ellos (26 días; también 4 en 2023 y 8 en 2025). Sin esos días ni 2024 ni 2025 son clasificables y la última campaña pasa a ser 2023. Siguen sin verificarse su origen y las condiciones de uso de los datos de INTA. Ver `AGENTS.md` y `test_clima_procedencia.py`.
- **Hallazgos medios y menores de la clarificación.** Quedan como dudas abiertas, con el comportamiento provisional de la sección 8 del plan.
- **Documentación del repo original.** Pendiente (lo edita la persona responsable, no el sandbox): FC citado como 1,2262, Welch por defecto y duplicados.
