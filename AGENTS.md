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

- **2.303 días (`INTA_verificado`)** son idénticos, día por día, al Excel `EEA_Miramar.xls` de INTA
  (estación Miramar – EEA Balcarce, id A872819): 0 diferencias en Tmax y Tmin.
- **301 días (`no_verificado`) NO están verificados.** O están vacíos en ese Excel (58 días anteriores al
  2025-07-28) o vienen después de su fin (243 días, del 2025-07-29 al 2026-03-28). 35 de ellos son
  claramente valores derivados (2 decimales o más: promedios o interpolaciones); los otros 266 tienen 1
  decimal, como INTA, y podrían ser una descarga posterior de INTA, pero no se pudo comprobar. Se
  desconoce su origen exacto.
- **Los inviernos 2024 y 2025 dependen de esos días** (26 y 42 días de mayo a agosto). Sin ellos, ninguno
  de los dos es clasificable y la última campaña clasificable pasa a ser la 2023. Lo prueba
  `tests/test_clima_procedencia.py`: no leer las horas de frío de 2024 y 2025 como más firmes de lo que son.
- El archivo vino de una carpeta de preparación de subidas de otro proyecto; no hay documento que lo
  describa. Las condiciones de uso de los datos de INTA no se verificaron: el repositorio es privado, y
  conviene confirmarlas antes de abrirlo.

## Verificación obligatoria
Antes de dar una tarea por terminada: correr los tests y mostrar el resultado.
Una tarea a la vez, tests primero.
