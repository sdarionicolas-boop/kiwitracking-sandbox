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
- **58 días (`no_verificado`) NO están verificados:** INTA los tiene vacíos en ambas descargas (entre
  2019-09-24 y 2025-05-12). 35 de ellos son claramente valores derivados (2 decimales o más: promedios o
  interpolaciones); los otros 23 tienen 1 decimal, como INTA, pero no se pudo comprobar su origen. Solo
  otra fuente de datos, o quien armó el archivo, puede resolverlos.
- **El invierno 2024 depende de esos días** (26 días de mayo a agosto; también 4 en 2023 y 8 en 2025). Sin
  ellos, 2024 y 2025 no son clasificables (2025 por un hueco de 12 días, aunque su cobertura es 0,902) y la
  última campaña clasificable pasa a ser la 2023. Lo prueba `tests/test_clima_procedencia.py`: no leer las
  horas de frío de 2024 y 2025 como más firmes de lo que son.
- El archivo vino de una carpeta de preparación de subidas de otro proyecto; no hay documento que lo
  describa. Las condiciones de uso de los datos de INTA no se verificaron: el repositorio es privado, y
  conviene confirmarlas antes de abrirlo.

## Verificación obligatoria
Antes de dar una tarea por terminada: correr los tests y mostrar el resultado.
Una tarea a la vez, tests primero.
