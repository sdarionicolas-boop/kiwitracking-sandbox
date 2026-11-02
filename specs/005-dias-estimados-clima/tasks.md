# Tareas — Spec 005

Estado: BORRADOR. Una tarea a la vez, en este orden. Regla de cada tarea (constitución #5): primero el test (que lleva el número de RF), se ve fallar, después el código mínimo, y al final se corre toda la suite con `-W error`. Al cerrar un grupo de tareas se hacen mutaciones.

Lee: `spec.md` (RF-1 a RF-11), `clarificacion.md` y `plan.md`.

## Parámetro y entrada

- [x] **T5.0. Parámetro `origenes_estimados`.** `clima_parametros.py`.
  - Cubre: RF-9.
  - Hecho cuando: `ParametrosClima().origenes_estimados` es `("interpolado",)`; una lista se convierte en tupla; una lista vacía, un valor que no es lista ni tupla, un elemento que no es texto y un texto vacío o de solo espacios dan `ErrorDeEntrada` con los valores permitidos; los demás parámetros y sus valores por defecto no cambian.

- [ ] **T5.1. Preparar el clima con `origen`.** `clima_entrada.preparar_clima_con_origen`.
  - Cubre: RF-3 (parte de la preparación), RF-4, RF-5.
  - Hecho cuando: con la columna `origen`, la tabla preparada trae una columna booleana `estimado` (la etiqueta, sin espacios y sin distinguir mayúsculas, está en `origenes_estimados`, **y** el día está disponible); una celda vacía, una etiqueta numérica y una etiqueta fuera de la lista no son estimadas; con una fecha repetida se usa el `origen` de la primera aparición; sin la columna `origen` no hay columna `estimado`; el resultado no depende del orden de las filas ni de las columnas extra; `preparar_clima` devuelve exactamente lo de antes (los tests de la spec 002 pasan sin cambios).

## Núcleo

- [ ] **T5.2. Recuento por ventana.** `clima_origen.contar_estimados` y `ResultadoClima.estimados`.
  - Cubre: RF-1, RF-2, RF-3, RF-5.
  - Hecho cuando: `calcular_clima` devuelve `estimados` con una fila por ventana con al menos un día disponible (`periodo`, `dias_estimados`, `proporcion_estimada` sobre los días disponibles); un clima armado a mano da los valores contados a mano (ninguno, todos, algunos, con días sin temperaturas y con una ventana incompleta); sin la columna `origen`, `estimados` queda sin filas y la tabla `frio`, `COLUMNAS_FRIO` y las advertencias son idénticas a las de antes; el campo tiene valor por defecto vacío (los `ResultadoClima` armados a mano siguen funcionando).

- [ ] **T5.3. Estado de la campaña y aviso.** `campana.estado_frio_de_campana`.
  - Cubre: RF-6, RF-7, RF-8, RF-2.
  - Hecho cuando: `EstadoCampana` trae `dias_estimados` y `proporcion_estimada` del período elegido (con `campana` indicada y sin indicar); si son mayores que 0 sale `DIAS_ESTIMADOS` con el período, los días estimados, los disponibles, el porcentaje y la aclaración de que no son mediciones, **después** de `CAMPANA_NO_INDICADA` y `COBERTURA_PARCIAL`; con 0 días, sin recuento o sin fila para el período no hay aviso y los valores quedan en 0 o en `None`; el estado, las horas y las demás advertencias son idénticos con y sin la columna `origen`; los campos nuevos están al final y con valor por defecto (las construcciones posicionales de los tests siguen funcionando).

## Flujo, resumen y línea de comandos

- [ ] **T5.4. Estado en el flujo y en `resumen.json`.** `flujo.py` y `salida.py`.
  - Cubre: RF-11.
  - Hecho cuando: `EstadoDeFrio` trae `dias_estimados` y `proporcion_estimada` del estado de `clima` (y `None` con estado manual o sin estado); `resumen.json` los escribe en `estado_frio` a continuación de `hueco_maximo` cuando el origen es `clima`, con `null` si el clima no trae `origen`, y no los agrega con estado manual o sin estado; `parametros.clima` incluye `origenes_estimados` como lista, siempre que haya `--clima`, a continuación de `campana`; se actualiza el test de la spec 003 que compara el diccionario completo (gana la clave); la advertencia `DIAS_ESTIMADOS` llega a `advertencias.json` en su lugar del orden.

- [ ] **T5.5. Opción `--origenes-estimados`.** `cli.py`.
  - Cubre: RF-10.
  - Hecho cuando: `analizar --clima clima.csv --origenes-estimados a,b` pasa `["a", "b"]` (sin espacios al inicio ni al final) a `ParametrosClima`; sin indicarla se usa el valor por defecto de `ParametrosClima` (no se copia); un valor vacío (`""`, `a,,b`) da un error de entrada con código 1; la opción sin `--clima` da el error de las demás opciones de clima (sola y junto con `--estado-frio`); aparece en la ayuda en español.

## Datos reales

- [ ] **T5.6. Clima real (criterios 3 a 5).** `test_clima_estimados_golden.py`.
  - Cubre: criterios 3, 4 y 5.
  - Hecho cuando: con `clima_diario.csv` el recuento da 4 de 123 en 2023, 26 de 123 en 2024 (21,1 %) y 8 de 119 en 2025; `analizar --clima --campana 2024` trae `DIAS_ESTIMADOS` con esas cifras y `resumen.json` registra `dias_estimados` 26; sin `--campana` el aviso es el de 2025; con y sin la columna `origen` las recomendaciones (16 "Mantener" y 19 "Intervenir"), el estado "Óptimo" y las 1.128,8 horas de 2024 son los mismos; sin la columna `origen`, `resumen.json` trae `null` en los dos campos y no sale ninguna advertencia nueva.

## Cierre

- [ ] **T5.7. Validación final.**
  - Cubre: criterio 6 de la spec (cada RF con test).
  - Hecho cuando: existe `validacion.md` con la matriz de los 11 RF contra sus tests y el estado de cada criterio; la suite completa pasa con `-W error` **sin tests saltados**; se hicieron mutaciones (qué cuenta como estimado, la proporción sobre disponibles y no sobre esperados, un día sin temperaturas, la primera aparición de una fecha repetida, el orden de la advertencia, que el aviso no cambie el estado, las claves del resumen, la lista por defecto) y cada una hace fallar al menos un test; el trabajo queda commiteado.

## Notas

- Orden de dependencia: T5.0 (parámetro) → T5.1 (entrada) → T5.2 (recuento) → T5.3 (aviso) → T5.4 (flujo y resumen) → T5.5 (línea de comandos) → T5.6 (datos reales) → T5.7.
- El único test existente que se modifica es el de la spec 003 que compara el diccionario `parametros.clima` (T5.4). Si otra tarea obliga a modificar un test existente, se corta y se consulta.
- Las dudas abiertas de la clarificación (C4 a C7) no tienen tarea: se resuelven con los comportamientos provisionales de la sección 8 del plan.
