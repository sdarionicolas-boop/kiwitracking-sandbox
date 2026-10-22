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

## Verificación obligatoria
Antes de dar una tarea por terminada: correr los tests y mostrar el resultado.
Una tarea a la vez, tests primero.
