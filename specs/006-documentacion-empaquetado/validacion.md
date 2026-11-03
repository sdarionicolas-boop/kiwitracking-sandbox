# Validación — Spec 006

Fecha de la corrida: 03/11/2026. Comando: `.venv\Scripts\python -m pytest -W error -rs` → **1.549 tests, 1.549 pasan, 0 avisos, 0 saltados** (1.357 de las specs 001 a 005 y 192 de la spec 006). Además, `scripts/probar_instalacion.py` se corrió una vez de verdad (sección 4): código 0.

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`; cuenta cada caso de los tests parametrizados). Los números salen de los nombres de los tests, no de una lectura semántica.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 15 | OK | test_readme | Contenido del README (qué hace, qué no hace, instalación, enlace a la guía, cómo citar, licencia), sin garantías sin respaldo, y su ejemplo mínimo **ejecutado** sobre archivos armados desde `tests/golden/` (159 plantas, 53 bajo malla, estado "Óptimo") |
| 2 | 11 | OK | test_docs, test_docs_estructura | Los nueve encabezados de la guía en el orden de la spec, sin la palabra "borrador"; contenido de la instalación, el recorrido y la generación de paquetes |
| 3 | 13 | OK | test_docs | Todas las opciones de `kvpi`, `mapa` y `analizar` (y `--help`/`--version`) contra el analizador de argumentos; valores por defecto contra las firmas del código; las obligatorias marcadas; cada ejemplo aceptado por el analizador |
| 4 | 8 | OK | test_docs_advertencias | Los 26 códigos de advertencia del código fuente (extraídos con `ast`) contra la tabla de la guía, en los dos sentidos, sin repetidos, en orden alfabético y con significado y qué hacer |
| 5 | 4 | OK | test_docs_advertencias | Los códigos de salida 0, 1, 2 y 3 con su significado, el formato de los mensajes de error y que el programa devuelve esos códigos |
| 6 | 8 | OK | test_docs_formatos | Cada columna obligatoria que la guía declara para serie, muestreo, plantas y clima es exigida por el código; malla (formato y sistema de coordenadas); formato común de los CSV |
| 7 | 7 | OK | test_docs_formatos | Las columnas de `plantas_kvpi.csv` y `plantas.csv` (en su orden) y todas las claves de `resumen.json` y `advertencias.json` de una corrida real contra la guía, y que la guía no nombra claves que no existen |
| 8 | 19 | OK | test_docs_reproduccion | Las dos partes rotuladas de la reproducción: los bloques marcados se **ejecutan** y dan cada número de la guía (53/106, FC 1,2262, p de 1,0e-26 con Student, 0 y 19, comparación con el CSV publicado; estado "Óptimo", 16/19, 15 sin escalar, `DIAS_ESTIMADOS` 26 de 123); los 16 "Mantener" solo aparecen en la parte 2 |
| 9 | 10 | OK | test_docs_estructura | Límites: Earth Engine, Welch contra Student, días interpolados (cifras del archivo), internet, dónde se probó, qué está verificado (1e-12) y qué no, DOI de la versión, sin garantías |
| 10 | 4 | OK | test_docs, test_readme | Ejemplos de una sola línea, con barras comunes y sin rutas del equipo de quien escribió la guía o el README |
| 11 | 11 | OK | test_pyproject | Metadatos de `pyproject.toml`: versión 1.2.0, descripción sin "Sandbox", licencia SPDX, autor sin correo, Python 3.14, pisos de dependencias probados (y las versiones instaladas los cumplen), clasificadores solo de lo probado, sin URLs, extra `dev` |
| 12 | 2 | OK | test_pyproject | `LICENSE` MIT con el titular del repositorio original y texto completo |
| 13 | 28 | OK | test_empaquetado | Construcción sin errores ni avisos; contenido exacto del `wheel` (solo el paquete, sus metadatos y la licencia) y del `sdist` (lista de inclusión de `MANIFEST.in`, nada de `specs/`, `mapa.html`, `resultados/`, `.xls`…); metadatos y punto de entrada |
| 14 | 29 | OK | test_probar_instalacion, test_probar_instalacion_pasos | El script sin red: cada paso interno (versión, ayuda, ubicación del paquete, ejemplo mínimo con la huella), manejo de errores, limpieza. **Más** la corrida real (sección 4) |
| 15 | 9 | OK | test_version | `__version__` contra `pyproject.toml` (con el aviso de reinstalar), `--version` (salida y código 0, también en un proceso aparte), valor de reserva `desconocida`, y el número no está escrito en el código |
| 16 | 4 | OK | test_pyproject | Los módulos de terceros que importa el paquete son exactamente las dependencias declaradas |
| 17 | 9 | OK | test_pyproject | `CITATION.cff`: campos obligatorios, versión 1.2.0, autoría sin correo, tesis, DOI del proyecto (no de esta versión), sin fecha ni enlace al repositorio privado |

**Ninguno de los 17 RF queda sin test.** El más delgado es RF-12 (2 tests); alcanza para el texto de la licencia. El único test sin número de RF es el del `.gitignore` (`dist/`, `build/` y los `.xls` de INTA).

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests `RF-n` pasan, con avisos como errores | **Cumplido** | 1.549/1.549 con `-W error` |
| 2 | La guía no se desactualiza: los tests de RF-3, RF-4 y RF-5 la comparan con el analizador, el código fuente y los códigos de salida | **Cumplido** | `test_docs`, `test_docs_advertencias` (más `test_docs_formatos`, que compara columnas y claves con salidas reales) |
| 3 | Se reproduce la tesis y se distingue de lo nuevo | **Cumplido** | `test_docs_reproduccion`: los comandos de las dos partes dan los números de la guía; la parte 2 dice "no es lo publicado" |
| 4 | Se construye y se instala: el `wheel` se instala en un entorno limpio y `--version`, `--help` y el ejemplo mínimo funcionan desde otra carpeta | **Cumplido** | `test_empaquetado` (construcción) y la corrida real de `scripts/probar_instalacion.py` (sección 4) |
| 5 | El contenido del `wheel` y del `sdist` es el de RF-13 | **Cumplido** | `test_empaquetado` |
| 6 | Cada requisito tiene al menos un test | **Cumplido** | Sección 1 (17 RF) |

## 3. Mutaciones

Cada cambio se aplicó con un script que verifica que el patrón existe, se corrieron todos los tests de la spec 006 con `-W error` y se restauró el archivo.

| Mutación | Resultado |
|---|---|
| Una opción nueva del analizador sin documentar | Detectada |
| Un código de advertencia sin documentar | Detectada |
| Un valor por defecto cambiado en el código | Detectada |
| Un número de la reproducción cambiado en la guía | Detectada |
| Un archivo de más en el `sdist` (`mapa.html` en `MANIFEST.in`) | Detectada |
| Un archivo de más en el `wheel` (`tests` entre los paquetes) | Detectada |
| Una versión desfasada (`pyproject.toml` en 1.2.1) | Detectada |
| Una dependencia de más | Detectada |
| La cita con otra versión | Detectada |
| Una licencia distinta | Detectada |
| Un ejemplo mínimo roto en el README | Detectada |
| Una sección de la guía que falta | Detectada |
| Sin la opción `--version` | Detectada |
| El script de instalación sin comparar la versión | Detectada |

Durante T6.0 a T6.11 se hicieron además mutaciones por tarea (más de 200 en total). Sobrevivieron algunas y se resolvieron de dos maneras: tests más estrictos (por ejemplo, exigir un enlace y no solo un nombre, o una frase exacta en lugar de una palabra suelta) o aceptándolas como equivalentes y anotándolas en la tarea (sacar `license-files`, porque `setuptools` incluye `LICENSE` por defecto).

## 4. Prueba de instalación en un entorno limpio (RF-14)

`python scripts/probar_instalacion.py`, corrido el 03/11/2026 en Windows 11 con Python 3.14.0, versión 1.2.0 → **código 0, 82 s en total**:

| Paso | Duración |
|---|---|
| Construir el `wheel` y el `sdist` (`python -m build`, aislado) | 9,7 s |
| Crear un entorno virtual nuevo | 6,3 s |
| Instalar `kiwitracking-1.2.0-py3-none-any.whl` con sus dependencias (pip, con internet) | 44,3 s |
| `kiwitracking --version` | 10,9 s |
| `kiwitracking --help` | 2,0 s |
| `python -m kiwitracking --help` | 1,8 s |
| Ubicar el paquete importado (es el del entorno nuevo, no el del repositorio) | 0,1 s |
| Ejemplo mínimo del README: `kvpi`, `mapa` y `analizar` | 1,7 s, 1,9 s y 1,8 s |

La corrida real confirma lo que la guía afirma: `pip install` del archivo `.whl` crea el comando `kiwitracking` y el flujo completo anda desde otra carpeta. Hay que repetirla con cada versión nueva.

## 5. Correcciones a la spec durante la implementación

Cinco puntos se aclararon o corrigieron al escribir el código, siempre con la spec primero:
- **DOI (T6.0).** Se había escrito que el DOI de Zenodo era el de la `1.1.0`. Se comprobó que `10.5281/zenodo.19352552` redirige a un registro cuya versión figura como v1.0.1 (archivo `v1.0.2`); es el DOI del proyecto, y así quedó en RF-11 y RF-17.
- **`kiwitracking.egg-info` viejo (T6.4).** `setuptools` suma al `sdist` los archivos del `SOURCES.txt` viejo aunque `MANIFEST.in` no los nombre. Se agregó el caso límite: el test y el script lo borran antes de construir y la guía lo explica.
- **Extra `dev` (T6.1).** Incluye `setuptools>=77` además de `pytest` y `build`, porque los tests construyen sin entorno aislado.
- **README y guía provisionales (T6.1 y T6.4).** Hizo falta un `README.md` y un `docs/uso.md` mínimos desde el principio, porque `pyproject.toml` y `MANIFEST.in` los nombran; las tareas T6.5 a T6.10 los reemplazaron.
- **Reproducción (T6.8).** Se comprobó empíricamente por qué salen 16 "Mantener" y no 15 (el estado de frío "Óptimo" deja 15, y escalar el desvío suma una más), y se agregó una tercera corrida a la guía para separar los dos efectos.

## 6. Limitaciones y dudas abiertas

- **Discrepancia del DOI en tu repositorio original.** El badge del README original usa `…553` y su `CITATION.cff` usa `…552`; además Zenodo muestra la versión v1.0.1 mientras el `CITATION.cff` dice 1.1.0. Conviene revisarlo en la cuenta de Zenodo antes de citar.
- **Solo Python 3.14 y Windows 11.** Se declara y se prueba únicamente eso; ampliar el rango (Python 3.10 y versiones anteriores de las dependencias) queda para otra spec.
- **Sin `project.urls`.** El repositorio es privado y no hay una URL pública que poner.
- **`pip install` del `.whl` verificado una vez.** La corrida de la sección 4 es de una fecha y una versión; no corre sola con cada `pytest`.
- **Mensajes de `argparse`.** Los errores de uso (código 2) y el encabezado `options:` de la ayuda salen en inglés.
- **El `sdist` lleva los datos del lote de referencia** (coordenadas de las 159 plantas y el clima de INTA), decisión C2; quien lo comparta tiene que saberlo.
- **No se publicó nada.** Ni en PyPI ni en ningún otro índice; los archivos se generan localmente.
- **Hallazgos menores C9 a C14.** Todos se resolvieron con las decisiones del plan: `setuptools>=77` con licencia SPDX (C9), `dist/` y `build/` en el `.gitignore` (C10), ejemplos en una línea con barras comunes (C11), el aviso de internet para las teselas (C12), sin correo ni URL en los metadatos (C13) y los bloques ejecutables marcados con un comentario HTML (C14).
