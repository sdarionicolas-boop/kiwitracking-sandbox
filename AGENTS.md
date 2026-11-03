# AGENTS.md — KiwiTracking sandbox

## Proyecto
Sandbox para reescribir la metodología de KiwiTrackingIA (índice KVPI, corrección por malla,
GDD, horas de frío) como paquete Python testeable, siguiendo Spec-Driven Development (SDD).
El repo original (`../KiwiTrackingIA`) es de solo lectura: no se modifica desde acá.

## Flujo de trabajo (SDD)
Constitución → Spec → Clarificación → Plan → Tareas → Implementación → Validación → Cambio.
- `docs/constitution.md`: principios no negociables.
- `specs/NNN-nombre/{spec,plan,tasks}.md`: una carpeta por funcionalidad.
- No se escribe código sin spec aprobada. Un cambio de comportamiento empieza en la spec.

## Comandos
- Tests: `.venv\Scripts\python -m pytest` (PowerShell, desde la raíz del sandbox)
- Entorno: `python -m venv .venv` y `.venv\Scripts\python -m pip install -e .[dev]`

## Estilo
- Python 3.10+, pandas/numpy. Nombres en español para el dominio (`estabilidad`, `ambiente`),
  inglés para lo técnico.
- Sin rutas fijas: todo path llega por parámetro.

## Datos de referencia
`tests/golden/` contiene salidas reales del notebook 03 (v1.1, 20/06/2026). Son la verdad
contra la que se comparan los resultados. `horas_frio_por_temporada.csv` (abril 2026) es una
versión vieja y descartada: no usar.

## Datos de referencia del clima (spec 002)
`tests/golden/clima_diario.csv` trae las temperaturas diarias del lote de referencia (2.604 días, del
2019-01-01 al 2026-03-28, con 40 fechas sin dato que no se rellenan). Columnas: `date`, `Tmax`, `Tmin` y
`origen`; el núcleo ignora `origen`, pero deja la procedencia escrita junto al dato.

- **2.546 días (`INTA_verificado`)** son idénticos, día por día, a la estación Miramar – EEA Balcarce de INTA
  (id A872819), comparados con dos descargas: el Excel `EEA_Miramar.xls` (2.303 días, hasta 2025-07-28) y
  una descarga posterior hasta 2026-10-21 que confirmó los 243 días siguientes (22/10/2026): 0 diferencias en
  Tmax y Tmin.
- **58 días (`interpolado`) NO son mediciones:** INTA los tiene vacíos en ambas descargas (entre
  2019-09-24 y 2025-05-12). **Son valores interpolados, no mediciones:** SIGA muestra Tmax y Tmin vacíos en
  esos días (revisado a mano el 22/10/2026 para agosto de 2024) y 37 de los 58 coinciden exactamente con
  la interpolación lineal entre los días vecinos de INTA; el resto también sigue una recta, pero con otros
  extremos (por ejemplo, abril-mayo de 2025). El hueco es definitivo: no hay dato de la estación que lo
  llene.
- **El invierno 2024 depende de esos días** (26 días de mayo a agosto; también 4 en 2023 y 8 en 2025). Sin
  ellos, 2024 y 2025 no son clasificables (2025 por un hueco de 12 días, aunque su cobertura es 0,902) y la
  última campaña clasificable pasa a ser la 2023. Lo prueba `tests/test_clima_procedencia.py`: no leer las
  horas de frío de 2024 y 2025 como más firmes de lo que son.
- El archivo vino de una carpeta de preparación de subidas de otro proyecto; no hay documento que lo
  describa. La persona responsable informó (02/11/2026) que los datos de INTA no tienen
  condiciones de uso declaradas; al abrir el repositorio conviene igual citar a INTA (estación Miramar – EEA
  Balcarce, SIGA) como fuente.

## Datos de referencia de la serie de KVPI (spec 004)
`tests/golden/kvpi_serie.csv` es la serie de KVPI por planta y campaña exportada de Google Earth Engine el
24/10/2026 para el lote de referencia: 954 filas, 159 plantas por 6 campañas (`2019_2020` a `2024_2025`), sin
repetidos ni vacíos. Columnas: `system:index`, `KVPI`, `campaña`, `col`, `id`, `row` y `.geo`; el núcleo usa
`id`, `campaña` y `KVPI`. Promedio y desvío muestral (n−1) por `id` reproducen `KVPI_mean` y `KVPI_std` de
`datos_plantas_completos.csv` con diferencias máximas de 5,6e-17 y 9,7e-17.

- **Procedencia:** proyecto de Google Earth Engine `applied-oxygen-459415-e2` (informado por la persona
  responsable el 02/11/2026). Colección de imágenes: `COPERNICUS/S2_SR_HARMONIZED`, según los notebooks del repo
  original. Falta, si se quiere dejar completa, la fecha de corte de las imágenes (las colecciones de Earth Engine
  se reprocesan); sin ella, una diferencia con lo publicado en una exportación futura se investiga sin ese dato.
- El muestreo (`id`, `X`, `Y`) de las 159 plantas sale de `datos_plantas_completos.csv`: las coordenadas son
  idénticas a las de `muestreo_sistematico.csv` del repo original (verificado en la clarificación).

## Verificación obligatoria
Antes de dar una tarea por terminada: correr los tests y mostrar el resultado.
Una tarea a la vez, tests primero.
