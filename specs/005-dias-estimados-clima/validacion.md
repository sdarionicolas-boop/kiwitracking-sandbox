# Validación — Spec 005

Fecha de la corrida: 02/11/2026. Comando: `.venv\Scripts\python -m pytest -W error -rs` → **1.357 tests, 1.357 pasan, 0 avisos, 0 saltados** (1.230 de las specs 001 a 004 y 127 de la spec 005).

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`; cuenta cada caso de los tests parametrizados). Los números salen de los nombres de los tests, no de una lectura semántica.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 27 | OK | test_clima_origen | La columna `estimado` (etiqueta sin espacios y sin distinguir mayúsculas, lista configurable), el recuento por ventana en modo invierno y temporada, la proporción sobre los días disponibles (ventana incompleta incluida), ventanas completas, sin estimados y todas estimadas |
| 2 | 9 | OK | test_clima_origen, test_campana_estimados | Sin la columna `origen`: `estimados` sin filas y con sus tipos, `frio`, `gdd`, `COLUMNAS_FRIO` y advertencias idénticos, sin aviso; un `ResultadoClima` armado a mano sigue funcionando |
| 3 | 2 | OK | test_clima_origen | Un día sin una o las dos temperaturas no cuenta como estimado ni como disponible, aunque tenga la etiqueta |
| 4 | 2 | OK | test_clima_origen | Con una fecha repetida vale el `origen` de la primera aparición, también si no es la primera en orden cronológico; `FECHA_DUPLICADA` sigue saliendo |
| 5 | 3 | OK | test_clima_origen | El recuento no depende del orden de las filas ni de las columnas extra |
| 6 | 9 | OK | test_campana_estimados | `DIAS_ESTIMADOS` con período, días estimados, de cuántos disponibles, porcentaje y la aclaración de que no son mediciones; solo del período que decide el estado; sin aviso con 0 días, sin recuento o sin ventana clasificable |
| 7 | 3 | OK | test_campana_estimados | El aviso sale después de `CAMPANA_NO_INDICADA` y `COBERTURA_PARCIAL`, con y sin campaña indicada |
| 8 | 7 | OK | test_campana_estimados, test_cli_estimados | El aviso y la lista de etiquetas no cambian el estado, las horas, la cobertura, el hueco ni las demás advertencias |
| 9 | 16 | OK | test_clima_origen | `origenes_estimados`: valor por defecto, lista convertida en tupla, y los valores no permitidos (vacía, texto suelto, no texto, vacío o en blanco) con su error |
| 10 | 20 | OK | test_cli_estimados | `--origenes-estimados`: separación por comas, espacios, valores vacíos, solo con `--clima` (también con `--estado-frio` y junto a otras opciones), ayuda en español, códigos de salida y de punta a punta con el clima real |
| 11 | 17 | OK | test_flujo_estimados | `EstadoDeFrio` con el recuento, claves nuevas de `estado_frio` a continuación de `hueco_maximo` (`null` sin `origen`, ausentes con estado manual o sin estado), `parametros.clima` con `origenes_estimados` siempre, y el aviso en `advertencias.json` en su lugar |

**Ninguno de los 11 RF queda sin test.** Los más delgados son RF-3 y RF-4 (2 tests cada uno); alcanzan para su comportamiento. Los 12 tests sin número de RF son los de datos reales (`test_clima_estimados_golden`, 7) y algunos generales (no modificar la entrada, errores de validación que siguen igual, construcción posicional).

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests `RF-n` pasan, con avisos como errores | **Cumplido** | 1.357/1.357 con `-W error` |
| 2 | Clima sintético: recuento por ventana igual a lo contado a mano, con los casos límite | **Cumplido** | `test_clima_origen`: todos estimados, ninguno, fechas repetidas, días sin temperaturas, ventana incompleta, modo temporada |
| 3 | Clima real: 26 de 123 en 2024 (21,1 %), 4 de 123 en 2023 y 8 de 119 en 2025; el aviso y `dias_estimados` 26 en el resumen | **Cumplido** | `test_clima_estimados_golden`; las cifras salen del archivo (58 interpolados, 38 en los meses de frío) |
| 4 | Con y sin la columna `origen`: mismas recomendaciones (16 "Mantener" y 19 "Intervenir"), mismo estado "Óptimo" y mismas horas | **Cumplido** | `test_clima_estimados_golden`: `plantas.csv` idéntico byte a byte, 1.128,8 h en 2024 |
| 5 | Sin columna `origen`: `null` en los dos campos y ninguna advertencia nueva | **Cumplido** | `test_clima_estimados_golden` y `test_flujo_estimados` |
| 6 | Cada requisito tiene al menos un test | **Cumplido** | Sección 1 (11 RF) |

## 3. Mutaciones

Cada cambio se aplicó con un script que verifica que el patrón existe, se corrieron todos los tests de la spec 005 con `-W error` y se restauró el código.

| Mutación | Resultado |
|---|---|
| Qué cuenta como estimado (la etiqueta no se normaliza) | Detectada |
| Un día sin temperaturas cuenta como estimado | Detectada |
| El `origen` de la última aparición en vez de la primera | Detectada |
| Proporción sobre los días esperados y no los disponibles | Detectada |
| Un día fuera de los meses de frío cuenta | Detectada |
| El aviso sale antes que los demás | Detectada |
| El aviso cambia el estado | Detectada |
| Avisa aunque haya 0 días | Detectada |
| Claves del resumen fuera de orden | Detectada |
| Las claves nuevas se agregan con estado manual | Detectada |
| Lista de etiquetas por defecto distinta | Detectada |
| `parametros.clima` sin `origenes_estimados` | Detectada |
| Etiqueta vacía permitida en `--origenes-estimados` | Detectada |
| Sin la columna `origen`, `estimados` no queda vacío | Detectada |

Durante T5.0 a T5.6 se hicieron además mutaciones por tarea (más de 90 en total). Sobrevivieron algunas equivalentes y se anotaron en cada tarea: una conversión redundante a booleano (`isin` ya devuelve falso para los vacíos, y se quitó), el orden de la agrupación (la tabla preparada ya viene ordenada por fecha) y una mutación que no cambiaba nada.

## 4. Correcciones a la spec durante la implementación

- **Tests existentes que cambian (T5.4).** La spec decía que solo cambiaba uno. Cambian **tres** de la spec 003, todos por una consecuencia directa de RF-11: la comparación del diccionario completo de `parametros.clima` está en dos (`test_flujo` y `test_flujo_golden`, ganan `origenes_estimados`) y otro fija las claves de `estado_frio` con origen `clima` (`test_salida`, ganan `dias_estimados` y `proporcion_estimada`). Se consultó antes de tocarlos, se corrigió la spec y los demás 1.227 tests de la spec 001 a 004 no cambiaron.
- **Ninguna otra decisión de la spec cambió.** El resto se resolvió en la clarificación (C1 a C3) y está en la spec.

## 5. Limitaciones y dudas abiertas

- **Sin la columna `origen` no hay aviso.** El programa no puede saber si hay días estimados; tampoco avisa que no tiene con qué comparar cuando se indica `--origenes-estimados` (C5 y duda abierta de la spec). Una columna presente pero vacía da 0 sin aviso, igual que un clima totalmente medido.
- **Sin ventana clasificable no hay recuento ni aviso** (C4): no hay período que decida el estado.
- **Etiquetas.** Se comparan sin espacios y sin mayúsculas, pero no sin tildes; los textos que `pandas` lee como vacíos (`NA`, `null`, `N/A`) no se pueden listar (C6).
- **El mensaje afirma "no son mediciones".** Es cierto para `interpolado`; con una lista propia el programa no sabe qué significa la etiqueta (C7).
- **La proporción es sobre los días disponibles**, no sobre los esperados; con una ventana incompleta las dos cifras difieren.
- **El GDD no se avisa.** El GDD por temporada también usa días interpolados; no alimenta ninguna recomendación.
- **Datos de INTA.** Siguen sin verificarse las condiciones de uso antes de abrir el repositorio (ver `AGENTS.md`).
- **Fechas repetidas.** El clima real no tiene ninguna; la regla de la primera aparición se prueba solo con datos sintéticos.
