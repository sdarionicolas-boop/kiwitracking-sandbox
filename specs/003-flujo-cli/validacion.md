# Validación — Spec 003

Fecha de la corrida: 24/10/2026. Comando: `.venv\Scripts\python -m pytest -W error -rs` → **1.004 tests, 1.004 pasan, 0 avisos, 0 saltados** (797 de las specs 001 y 002 y 207 de la spec 003).

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`; cuenta cada caso de los tests parametrizados). Los números salen de los nombres de los tests, no de una lectura semántica.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 11 | OK | test_cli | Programa `kiwitracking`, subcomandos, ayuda en español, códigos 0 y 2, `python -m kiwitracking` en un proceso aparte, punto de entrada en `pyproject.toml` |
| 2 | 4 | OK | test_flujo | Lectura del CSV de plantas con la lectura de la spec 001 (BOM, codificación); archivo inexistente nombra el archivo |
| 3 | 5 | OK | test_flujo | Con malla: `bajo_malla` por el cruce, `--crs-plantas` obligatorio, sistemas distintos, advertencias del cruce, polígono devuelto |
| 4 | 2 | OK | test_flujo | Sin malla: se usa `bajo_malla` del CSV; sin malla y sin columna, error |
| 5 | 4 | OK | test_flujo | Malla y `bajo_malla` en el CSV: gana el cálculo y avisa cuántas plantas cambiaron (nada si ninguna) |
| 6 | 13 | OK | test_cli, test_flujo | Comando `mapa`: HTML, huella, cantidades, advertencias, salida por defecto, no sobrescribe sin `--sobrescribir`, no deja archivos si falla |
| 7 | 2 | OK | test_cli, test_flujo | `--sin-fondo-satelital`: el HTML no pide teselas (y con fondo sí) |
| 8 | 12 | OK | test_cli, test_flujo | Huella ausente (código 1, mensaje) o incorrecta, en cualquier modo de corrección incluido `forzar`; el mensaje no imprime la huella correcta |
| 9 | 12 | OK | test_cli, test_flujo | Parámetros indicados llegan a `analizar()` con sus nombres; valores por defecto sin copiar; valores no permitidos |
| 10 | 7 | OK | test_flujo | Estado de frío desde el clima (campaña indicada o la más reciente), parámetros de clima, formato de fecha, BOM |
| 11 | 12 | OK | test_cli, test_flujo | `--estado-frio` sin distinguir mayúsculas ni tildes; excluyente con `--clima`; origen `manual` |
| 12 | 2 | OK | test_flujo | Sin clima ni estado: origen `ninguno` y aviso `SIN_ESTADO_FRIO` |
| 13 | 5 | OK | test_flujo | Sin ventana clasificable no se detiene (dos avisos, causa y consecuencia); campaña inexistente o no clasificable da error |
| 14 | 2 | OK | test_flujo | Orden de las advertencias: cruce, clima, campaña, análisis |
| 15 | 3 | OK | test_salida | Tres archivos de resultados con su contenido (el resumen y la escritura se prueban también en RF-17, RF-25 y RF-27) |
| 16 | 5 | OK | test_salida | UTF-8 sin BOM, `\n` en cualquier sistema, números completos, celdas vacías |
| 17 | 12 | OK | test_cli, test_salida | Carpeta creada si no existe; error sin tocar nada si ya hay resultados; `--sobrescribir`; otros archivos de la carpeta se respetan |
| 18 | 4 | OK | test_cli | Resumen corto en pantalla: plantas, FC, recomendaciones, estado de frío, advertencias, dónde quedó todo |
| 19 | 8 | OK | test_cli | Códigos 0, 1, 2 y 3; `Error: <mensaje>` sin traza; error inesperado con mensaje corto y traza solo con `--depurar`; en un proceso aparte |
| 20 | 10 | OK | test_flujo, test_salida | Los archivos de entrada no se modifican; errores de datos antes de escribir; limpieza si falla la escritura |
| 21 | 1 | OK | test_cli | Rutas con espacios y con tildes |
| 22 | 1 | OK | test_cli | Consola forzada a ASCII: no falla al mostrar tildes (proceso aparte) |
| 23 | 16 | OK | test_coordenadas, test_flujo | Conversión a `EPSG:4326` para dibujar: ida y vuelta, sistemas mixtos, copias, vacíos, sin cambiar `bajo_malla` ni la huella |
| 24 | 16 | OK | test_cli | Opciones de clima sin `--clima` (solas o con `--estado-frio`): error que las nombra |
| 25 | 14 | OK | test_salida | `resumen.json`: JSON estricto, estructura y orden de claves, `null`, tipos de NumPy, estado de frío, sección `clima` |
| 26 | 1 | OK | test_cli | La huella sale en una línea propia con el formato exacto `Huella: <12 caracteres>` |
| 27 | 5 | OK | test_salida | Columnas de `plantas.csv`: orden fijo, resto en su orden, filas en el orden de entrada, columnas de resultado reemplazadas |

**Ninguno de los 27 RF queda sin test.** Los más delgados son RF-21, RF-22 y RF-26 (1 test cada uno); alcanzan para su comportamiento, y RF-21 y RF-22 se prueban de verdad con el programa real (rutas con tildes; consola en ASCII). Los tests con datos reales (`test_flujo_golden`, 11), los de errores de argumentos de `analizar` (`test_criterio6_*`, 8) y el de `--salida` que es un archivo (`test_c13_*`) no llevan número de RF en el nombre.

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests `RF-n` pasan, con avisos como errores | **Cumplido** | 1.004/1.004 con `-W error` |
| 2 | Mapa: 53 plantas bajo malla, 106 fuera y la huella del lote | **Cumplido** | `test_criterio2_*`: la huella es igual a `huella()` sobre `datos_plantas_completos.csv` |
| 3 | Flujo completo: 16 "Mantener" y 19 "Intervenir" con `--clima` y `--campana 2024`; sin campaña, "Adecuado" de 2025 con `CAMPANA_NO_INDICADA` | **Cumplido** | `test_criterio3_*`: el resumen registra "Óptimo", período 2024, 1.128,8 h y origen `clima` |
| 4 | Con `--no-escalar-std` y `--estado-frio Deficiente`, `plantas.csv` reproduce lo publicado | **Cumplido** | `test_criterio4_*`: `KVPI_corregido` con diferencia menor que 1e-9, mismo `ambiente` y `recomendacion`, 0 "Mantener" y 19 "Intervenir" |
| 5 | Huella incorrecta: código 1, incluso con `--correccion forzar`, sin escribir nada | **Cumplido** | `test_criterio5_*` y `test_rf8_*` |
| 6 | Cada error de entrada conocido da un mensaje claro, sin traza, y código 1 | **Cumplido** | `test_criterio6_*` (8 errores de argumentos) y `test_rf19_*` (huella, archivo inexistente, mapa existente, resultados existentes) |
| 7 | Mapa en otro sistema: mismas 53 plantas, misma huella, mismo dibujo (menos de 1e-6 grados) | **Cumplido** | `test_criterio7_*`: lote y malla en `EPSG:22185`, y plantas en metros con la malla en grados |
| 8 | Cada requisito tiene al menos un test | **Cumplido** | Sección 1 (27 RF) |

## 3. Mutaciones

Cada cambio se aplicó con un script que verifica que el patrón existe, se corrió la suite completa y se restauró el código.

| Mutación | Resultado |
|---|---|
| Código de salida de un error inesperado (3 → 1) | Detectada |
| Orden de columnas de `plantas.csv` | Detectada |
| `NaN` escrito tal cual (sin pasar a `null` y con `allow_nan=True`) | Detectada |
| Normalización de tildes de `--estado-frio` | Detectada |
| Conversión a `EPSG:4326` del mapa | Detectada |
| Conversión de la advertencia de huella en error | Detectada |
| Conversión de las plantas a `EPSG:4326` en `a_wgs84` | Detectada |

Durante T3.0 a T3.10 se hicieron además mutaciones por tarea (más de 120 en total). Sobrevivieron algunas equivalentes y se anotaron en cada tarea: una máscara de coordenadas vacías que `pyproj` 3.8 ya hace por sí mismo, una comprobación duplicada agregada a propósito y un `.astype(int)` redundante que se quitó.

## 4. Correcciones a la spec durante la implementación

Cuatro puntos de la spec se aclararon o corrigieron al escribir el código, siempre con la spec primero:
- **RF-8:** en la spec 001 una huella ausente o incorrecta es una advertencia y el análisis corre sin corrección; la spec 003 decía que era un error. La línea de comandos es más estricta y la convierte en error de entrada, y el núcleo no cambia.
- **RF-1, RF-5, RF-13, RF-25 y RF-27:** el código de salida sin subcomando (2), que `BAJO_MALLA_REEMPLAZADO` solo avisa si alguna planta cambió, que con `--clima` sin ventana clasificable el origen es `ninguno`, la sección `clima` de los parámetros usados y que la garantía del orden de `plantas.csv` vale para las columnas conocidas.

## 5. Limitaciones y dudas abiertas

- **El comando `kiwitracking` no está instalado en este entorno.** El punto de entrada está declarado en `pyproject.toml` y probado (`main`, `python -m kiwitracking`, el texto del archivo), pero crear el comando exige reinstalar el paquete (`pip install -e .[dev]`), que necesita red para descargar `setuptools`. No se hizo desde el sandbox.
- **Hallazgos menores de la clarificación (C13 a C17).** Siguen como dudas abiertas con la decisión provisional del plan: `--salida` que es un archivo da un error (implementado y probado), `advertencias.json` es una lista de objetos `codigo` y `mensaje` (implementado y probado), el punto de entrada se declara pero requiere reinstalar, `mapa.html` no es idéntico entre corridas, y no hay `--version`.
- **Mensajes de `argparse`.** Los errores de uso (código 2) usan los textos de `argparse` y pueden salir en inglés.
- **Huella copiada a mano.** No hay `--huella-desde` en esta versión.
- **Coordenadas.** Las columnas se llaman `X` e `Y`; no hay otras opciones.
- **Consola.** La salida se reconfigura con reemplazo de caracteres que la consola no admite, en vez de forzar UTF-8 como decía el plan (D12); queda para confirmar.
- **Sobrescribir.** Con `--sobrescribir`, si la escritura falla a mitad de camino, los archivos de la corrida anterior que ya se hubieran reemplazado no se recuperan; es el costo de no usar una carpeta temporal.
- **Datos de INTA.** Siguen sin verificarse las condiciones de uso antes de abrir el repositorio, y el invierno 2024 depende de 26 días interpolados (ver `AGENTS.md`).
