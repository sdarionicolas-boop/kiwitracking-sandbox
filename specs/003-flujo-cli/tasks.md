# Tareas — Spec 003

Estado: BORRADOR. Una tarea a la vez, en este orden. Regla de cada tarea (constitución #5): primero el test (que lleva el número de RF), se ve fallar, después el código mínimo, y al final se corre toda la suite con `-W error`. Al cerrar un grupo de tareas se hacen mutaciones.

Lee: `spec.md` (RF-1 a RF-27), `clarificacion.md` y `plan.md`.

## Esqueleto

- [x] **T3.0. Programa y ayuda.** `cli.py`, `__main__.py`, `pyproject.toml`.
  - Cubre: RF-1.
  - Hecho cuando: `main([])` y `main(["--help"])` muestran una ayuda en español con los subcomandos `mapa` y `analizar` y sus opciones; un subcomando desconocido da el error de uso (código 2); `main` devuelve el código y no llama a `sys.exit`; `pyproject.toml` declara el punto de entrada `kiwitracking`; un test corre `python -m kiwitracking --help` en un proceso aparte y comprueba código 0 y la ayuda.

## Coordenadas

- [x] **T3.1. Conversión a `EPSG:4326` para dibujar.** `io.a_wgs84`.
  - Cubre: RF-23.
  - Hecho cuando: con plantas y polígono en `EPSG:22185` se obtienen las coordenadas en longitud y latitud con diferencia menor que 1e-6 grados respecto del lote original; con plantas en un sistema y polígono en otro se convierten los dos; si ya están en `EPSG:4326` no cambian; devuelve copias y no modifica la tabla de entrada; no altera `bajo_malla` ni la huella (la huella no depende de las coordenadas); un sistema desconocido da un error que lo nombra.

## Flujo: lectura y mapa

- [x] **T3.2. Preparar las plantas y la malla.** `flujo.preparar_plantas`.
  - Cubre: RF-2, RF-3, RF-4, RF-5.
  - Hecho cuando: un archivo que no existe da un error que nombra el archivo; con `--malla` se exige `--crs-plantas` y se calcula `bajo_malla` con el cruce de la spec 001, incluidas sus advertencias; sin `--malla` se usa `bajo_malla` del CSV, y si no está da un error que pide la malla o esa columna; con `--malla` y `bajo_malla` en el CSV gana el cálculo y sale `BAJO_MALLA_REEMPLAZADO` con la cantidad de plantas que cambiaron.

- [x] **T3.3. Comando `mapa`.** `flujo.ejecutar_mapa` y el subcomando.
  - Cubre: RF-6, RF-7, RF-26 (línea de la huella), RF-23 (integración).
  - Hecho cuando: genera el HTML dibujando plantas y polígono convertidos; imprime la huella en una línea propia `Huella: <12 caracteres>`, la cantidad de plantas bajo malla y fuera, y las advertencias; la huella es igual a `huella()` de la tabla preparada; con `--sin-fondo-satelital` el HTML no contiene la dirección de las teselas; si el archivo existe y no se indicó `--sobrescribir`, da un error sin tocarlo; con `--sobrescribir` lo reemplaza.

## Flujo: análisis

- [ ] **T3.4. Argumentos de `analizar`.** `cli.py`.
  - Cubre: RF-8 (falta de huella), RF-9, RF-11, RF-24.
  - Hecho cuando: sin `--huella` da un error de entrada (código 1) con el mensaje de RF-8, antes de leer archivos; `--clima` junto con `--estado-frio` es un error que dice que son excluyentes; cualquiera de las cinco opciones de clima sin `--clima` (sola o con `--estado-frio`) da un error que nombra la opción; `--estado-frio` acepta `optimo`, `ÓPTIMO` y `Óptimo` y los convierte al texto exacto, y un valor desconocido da el error de la spec 001 con los tres permitidos; cada parámetro de la spec 001 y de la spec 002 llega al núcleo, y los valores por defecto son los de `analizar()` y `ParametrosClima` (un test los compara con la firma de la función, sin copiarlos); `--p-ambiente` toma dos números y `--max-hueco-dias ninguno` pasa `None`.

- [ ] **T3.5. Estado de frío del flujo.** `flujo.elegir_estado_de_frio`.
  - Cubre: RF-10, RF-12, RF-13, RF-14.
  - Hecho cuando: con clima y `campana=2024` sobre el clima real el estado es "Óptimo" del período 2024; sin `campana` es "Adecuado" de 2025 con `CAMPANA_NO_INDICADA`; con un clima sin ventana clasificable el análisis corre sin estado y salen `SIN_PERIODO_CLASIFICABLE` y después `SIN_ESTADO_FRIO`; una campaña inexistente o no clasificable da el error de la spec 002; con `--estado-frio` el origen es `manual`; sin ninguno el origen es `ninguno` y sale `SIN_ESTADO_FRIO`; las advertencias salen en el orden de RF-14: cruce, clima, campaña, análisis.

- [ ] **T3.6. Análisis y control de la huella.** `flujo.ejecutar_analisis`.
  - Cubre: RF-8 (huella incorrecta), RF-9.
  - Hecho cuando: con la huella correcta devuelve el resultado de `analizar()`; con una huella incorrecta o ausente (`HUELLA_NO_COINCIDE` o `FALTA_CONFIRMACION`), en cualquier modo de corrección incluido `forzar`, da un `ErrorDeEntrada` cuyo mensaje dice que el conjunto de plantas bajo malla es distinto, que se revisen `--plantas`, `--malla` y `--crs-plantas` y que se corra `mapa` de nuevo, y **no** contiene la huella correcta; el núcleo no se modifica.

## Salidas

- [ ] **T3.7. Contenido de los archivos de resultados.** `salida.py`.
  - Cubre: RF-15, RF-16, RF-25, RF-27.
  - Hecho cuando: `plantas.csv` lleva las columnas en el orden de RF-27, las demás de entrada después en su orden, las filas en el orden de entrada, y reemplaza las columnas de resultado que ya venían; sale igual aunque cambie el orden de columnas de la entrada; `resumen.json` tiene la estructura y el orden de claves de RF-25, escribe `null` para los vacíos, `NaN` e infinitos, números comunes para los tipos de NumPy y los decimales completos, y se lee con un lector estricto devolviendo los mismos valores; `advertencias.json` es una lista de objetos `codigo` y `mensaje` en el orden de RF-14; todos los archivos son UTF-8 sin BOM y con `\n`.

- [ ] **T3.8. Escritura con limpieza.** `salida.escribir_resultados`.
  - Cubre: RF-17, RF-20.
  - Hecho cuando: crea la carpeta si no existe; si ya hay alguno de los tres archivos y no se indicó `--sobrescribir`, da un error sin modificar nada; con `--sobrescribir` los reemplaza; si falla la escritura del segundo archivo (simulado), borra el primero y da un error de entrada que nombra el archivo y el motivo; si `--salida` es un archivo existente, da un error que lo dice; los archivos de entrada no cambian (se comparan sus bytes antes y después).

## Línea de comandos completa

- [ ] **T3.9. Pantalla y códigos de salida.** `cli.py`.
  - Cubre: RF-18, RF-19, RF-21, RF-22, RF-26.
  - Hecho cuando: `analizar` muestra un resumen corto (cantidad de plantas, FC y si se corrigió, cantidad por recomendación, estado de frío y su origen) y las advertencias, y dice dónde quedaron los archivos; un `ErrorDeEntrada` sale por la salida de errores como `Error: <mensaje>`, sin traza, con código 1; una excepción inesperada sale como `Error inesperado: <tipo>: <mensaje>` con código 3, y con `--depurar` se muestra además la traza; el uso incorrecto da código 2; las rutas con espacios y con tildes funcionan; la pantalla no falla aunque la codificación de la consola no admita "Ó" (se reconfigura con reemplazo); dos tests corren el programa en un proceso aparte: uno con un error de entrada (código 1, mensaje en la salida de errores, sin traza) y otro con la consola forzada a ASCII (`PYTHONIOENCODING=ascii`) que termina con código 0.

## Datos reales

- [ ] **T3.10. Flujo completo con el lote real (criterios 2 a 5 y 7).** `test_flujo_golden.py`.
  - Cubre: RF-6, RF-8, RF-10, RF-15, RF-23, RF-25, RF-27; criterios 2 a 5 y 7.
  - Hecho cuando: `mapa` sobre `datos_plantas_completos.csv` y `malla_zona.geojson` informa 53 plantas bajo malla y 106 fuera, con una huella igual a la de `huella()`; `analizar` con esa huella, `--clima clima_diario.csv` y `--campana 2024` da 16 "Mantener" y 19 "Intervenir" y `resumen.json` registra "Óptimo", período 2024 y origen `clima`; sin `--campana` el estado es "Adecuado" de 2025 y `advertencias.json` trae `CAMPANA_NO_INDICADA`; con `--no-escalar-std` y `--estado-frio Deficiente`, `plantas.csv` tiene el mismo `KVPI_corregido`, `ambiente` y `recomendacion` que `datos_plantas_completos.csv` (0 "Mantener", 19 "Intervenir"); una huella incorrecta con `--correccion forzar` da código 1 y no escribe nada; con el lote y la malla convertidos a `EPSG:22185` y declarados con `--crs-plantas`, `mapa` da las mismas 53 plantas bajo malla y la misma huella, y los puntos dibujados difieren en menos de 1e-6 grados.

## Cierre

- [ ] **T3.11. Validación final.**
  - Cubre: criterio 8 de la spec (cada RF con test).
  - Hecho cuando: existe `validacion.md` con la matriz de los 27 RF contra sus tests y el estado de cada criterio; la suite completa pasa con `-W error` **sin tests saltados**; se hicieron mutaciones (código de salida de un error inesperado, orden de columnas de `plantas.csv`, `allow_nan`, normalización de tildes de `--estado-frio`, conversión a `EPSG:4326` del mapa, conversión de la advertencia de huella en error) y cada una hace fallar al menos un test; el trabajo queda commiteado.

## Notas

- Orden de dependencia: T3.0 (esqueleto) → T3.1 (coordenadas) → T3.2 y T3.3 (lectura y mapa) → T3.4 a T3.6 (análisis) → T3.7 y T3.8 (salidas) → T3.9 (pantalla y códigos) → T3.10 (datos reales) → T3.11.
- Las tareas T3.2, T3.5 y T3.6 viven en `flujo.py` y se prueban sin consola; `cli.py` solo las llama. Si una tarea obliga a poner cálculo en `cli.py`, se corta y se mueve a `flujo.py`.
- Para que el comando `kiwitracking` exista hay que reinstalar el paquete con `.venv\Scripts\python -m pip install -e .[dev]` después de T3.0; los tests no dependen de eso (llaman a `main` y a `python -m kiwitracking`).
- Las dudas abiertas de la clarificación (C13 a C17) no tienen tarea: se resuelven con los comportamientos provisionales de la sección 8 del plan. C13 (`--salida` que es un archivo) y la limpieza de C8 se cubren en T3.8.
