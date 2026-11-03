# Tareas — Spec 006

Estado: BORRADOR. Una tarea a la vez, en este orden. Regla de cada tarea (constitución #5): primero el test (que lleva el número de RF), se ve fallar, después el código o el texto mínimo, y al final se corre toda la suite con `-W error`. Al cerrar un grupo de tareas se hacen mutaciones.

Lee: `spec.md` (RF-1 a RF-17), `clarificacion.md` y `plan.md`.

## Archivos base y metadatos

- [x] **T6.0. Licencia, cita y `.gitignore`.** `LICENSE`, `CITATION.cff`, `.gitignore`.
  - Cubre: RF-12, RF-17.
  - Hecho cuando: `LICENSE` es el MIT del repositorio original (mismo texto y año); `CITATION.cff` tiene `cff-version`, `message`, `title`, `authors` (nombre, afiliación y ORCID, **sin correo**), `version: 1.2.0`, `license: MIT`, la referencia a la tesis y el DOI de Zenodo identificado como el del proyecto (no el de esta versión); `.gitignore` incluye `dist/` y `build/` y su comentario sobre los `.xls` de INTA deja de decir "sin verificar"; los tests lo comprueban por texto, sin agregar dependencias.

- [x] **T6.1. Metadatos de `pyproject.toml`.**
  - Cubre: RF-11.
  - Hecho cuando: `pyproject.toml` declara nombre, versión `1.2.0`, descripción en español sin la palabra "Sandbox", `readme = "README.md"`, `license = "MIT"` con `license-files`, autor sin correo, `requires-python = ">=3.14"`, dependencias con los pisos probados (`pandas>=3.0`, `numpy>=2.5`, `scipy>=1.18`, `shapely>=2.2`, `pyproj>=3.8`, `folium>=0.20`), clasificadores (solo Python 3.14, sin sistema operativo), palabras clave, `build-system` con `setuptools>=77`, y el extra `dev` con `pytest`, `build` y `setuptools>=77` (los tests construyen sin entorno aislado); no hay `project.urls`; un test comprueba que las versiones instaladas cumplen los pisos; el entorno de desarrollo se reinstala con `pip install -e .[dev]`.

- [x] **T6.2. Versión y `--version`.** `kiwitracking/__init__.py`, `cli.py`.
  - Cubre: RF-15.
  - Hecho cuando: `kiwitracking.__version__` es la de los metadatos instalados y coincide con la de `pyproject.toml` (si no, el mensaje del test dice que hay que reinstalar con `pip install -e .`); sin metadatos vale `desconocida`; `main(["--version"])` imprime `kiwitracking 1.2.0`, devuelve 0 y no llama a `sys.exit`; también vale con `python -m kiwitracking --version` en un proceso aparte; con metadatos ausentes imprime `kiwitracking desconocida` sin fallar; los tests existentes de la ayuda siguen pasando sin cambios.

- [ ] **T6.3. Dependencias contra imports.**
  - Cubre: RF-16.
  - Hecho cuando: un test recorre los imports de `kiwitracking/*.py` con `ast`, descarta la biblioteca estándar (`sys.stdlib_module_names`) y el propio paquete, y comprueba que el resto es exactamente el conjunto de dependencias de `pyproject.toml` (ni de más ni de menos).

## Construcción

- [ ] **T6.4. Construcción y contenido del `wheel` y del `sdist`.** `MANIFEST.in`.
  - Cubre: RF-13.
  - Hecho cuando: `python -m build --no-isolation` en una carpeta temporal genera `kiwitracking-1.2.0-py3-none-any.whl` y `kiwitracking-1.2.0.tar.gz` sin errores ni avisos; el `wheel` contiene exactamente los módulos de `kiwitracking/`, los metadatos (`METADATA`, `WHEEL`, `entry_points.txt`, `top_level.txt`, `RECORD`) y `LICENSE`, y su punto de entrada es `kiwitracking = kiwitracking.cli:main`; el `sdist` contiene solo la lista de inclusión de la spec (`kiwitracking/`, `tests/` con `tests/golden/`, `docs/uso.md`, `README.md`, `LICENSE`, `CITATION.cff`, `pyproject.toml` y los metadatos que genera la herramienta) y ningún archivo de `specs/`, ni `AGENTS.md`, `CLAUDE.md`, `docs/constitution.md`, `mapa.html`, `resultados/`, `.xls`, `.venv`, `dist/` ni `build/`. (`docs/uso.md` y `README.md` todavía no existen: el test usa archivos mínimos temporales hasta T6.10.)

## Guía de uso

- [ ] **T6.5. Guía: instalación, recorrido y opciones.** `docs/uso.md` (secciones 1 y 2).
  - Cubre: RF-3, RF-10, RF-2 (parte).
  - Hecho cuando: existen las secciones "Requisitos e instalación" y "Recorrido completo"; cada opción larga de `kvpi`, `mapa` y `analizar` (las del analizador de argumentos, incluidas `--help` y `--depurar`) y la general `--version` figuran en una línea `` - `--opcion` `` con su descripción; las que tienen valor por defecto en el código (firmas de `analizar`, `ParametrosClima` y `ejecutar_kvpi`) terminan en `(por defecto: <valor>)` con el valor que dan esas firmas; los ejemplos están en una línea, con barras comunes y sin rutas del equipo de quien escribió la guía; un test falla si se agrega una opción al analizador sin documentarla o si la guía nombra una que no existe.

- [ ] **T6.6. Guía: formatos de entrada y archivos de salida.** `docs/uso.md` (secciones 3 y 4).
  - Cubre: RF-6, RF-7.
  - Hecho cuando: para `serie`, `muestreo`, `plantas`, `malla` y `clima` la guía lista las columnas obligatorias y opcionales (las que validan `validar_serie`, `preparar_muestreo`, la lectura de la spec 001, la malla y `preparar_clima`), la codificación UTF-8, el punto decimal y el sistema de coordenadas de `--crs-plantas`; describe las columnas de `plantas_kvpi.csv` y de `plantas.csv`, la estructura de `resumen.json` (sus claves, incluidas `dias_estimados` y `proporcion_estimada`) y la de `advertencias.json`; tests comprueban que cada columna obligatoria que exige el código figura en la guía y que las claves de un `resumen.json` generado están todas documentadas.

- [ ] **T6.7. Guía: advertencias y códigos de salida.** `docs/uso.md` (secciones 5 y 6).
  - Cubre: RF-4, RF-5.
  - Hecho cuando: una tabla lista los 26 códigos de advertencia que el programa emite (los extrae un test con `ast`) con su significado y qué hacer; los códigos de salida 0, 1, 2 y 3 figuran en una tabla con su significado; los tests fallan si el código emite una advertencia que la guía no lista o si la guía lista una que ya no existe.

- [ ] **T6.8. Guía: reproducir los resultados de la tesis.** `docs/uso.md` (sección 7).
  - Cubre: RF-8.
  - Hecho cuando: hay dos partes rotuladas, "Reproducir lo publicado" (`mapa` y `analizar` con `--prueba-t student --no-escalar-std --estado-frio Deficiente`) y "Lo que agrega el programa" (`analizar` con el clima y `--campana 2024`), con bloques marcados con `<!-- prueba: … -->`, el marcador `HUELLA` y la tabla de resultados esperados; la sección dice que necesita `tests/golden/` (repositorio o `sdist`, no el `wheel`); un test ejecuta los bloques con `main(argv)` sobre una copia de `tests/golden/` y comprueba cada número de la tabla (53 y 106, FC 1,2262, p ≈ 1,0e-26, 0 y 19 en la parte 1; estado "Óptimo", 1.128,8 h, 16 y 19 y `DIAS_ESTIMADOS` 26 de 123 en la parte 2) y que ese número aparece en la guía; la parte 2 aclara que no es lo publicado.

- [ ] **T6.9. Guía: generar los paquetes y límites; orden de los encabezados.** `docs/uso.md` (secciones 8 y 9).
  - Cubre: RF-9, RF-2.
  - Hecho cuando: la sección "Generar los paquetes" explica `pip install -e .[dev]`, `python -m build` y `scripts/probar_instalacion.py`; "Límites del programa" dice qué no hace (el paso de Google Earth Engine), la diferencia entre la prueba t por defecto (Welch) y la de la tesis (Student), los días interpolados del clima y su efecto, que `mapa` necesita internet para el fondo satelital, que solo se probó en Windows 11 con Python 3.14, y que la `1.2.0` no tiene DOI propio; ninguna afirmación sin un test o un dato detrás; un test comprueba que los nueve encabezados están y en el orden de RF-2.

## README

- [ ] **T6.10. README y ejemplo mínimo.** `README.md`.
  - Cubre: RF-1, RF-10.
  - Hecho cuando: el README dice qué hace y qué no, cómo instalar, el ejemplo mínimo con los tres comandos (en un bloque marcado, con `HUELLA`), el enlace a `docs/uso.md`, la licencia y una sección "Cómo citar" que remite a `CITATION.cff`; un test ejecuta el ejemplo mínimo con `main(argv)` sobre archivos armados desde `tests/golden/` y da código 0; ninguna ruta del equipo de quien escribió la guía; el test de T6.4 pasa ahora con los archivos reales.

## Instalación en un entorno limpio

- [ ] **T6.11. Script de instalación.** `scripts/probar_instalacion.py`.
  - Cubre: RF-14.
  - Hecho cuando: el script construye los paquetes, crea un entorno virtual nuevo, instala el `wheel` con sus dependencias desde internet, y desde una carpeta que no es la del código corre `kiwitracking --version`, `kiwitracking --help`, `python -m kiwitracking --help` y el ejemplo mínimo del README con archivos de `tests/golden/`; devuelve un código distinto de 0 y dice qué falló si algo no anda; se corrió una vez y su resultado, con la fecha, la versión y la duración, quedó anotado para `validacion.md`. Un test sin red comprueba que el script existe y que su ayuda y su manejo de errores funcionan (sin crear el entorno).

## Cierre

- [ ] **T6.12. Validación final.**
  - Cubre: criterio 6 de la spec (cada RF con test).
  - Hecho cuando: existe `validacion.md` con la matriz de los 17 RF contra sus tests (RF-14 contra la corrida del script) y el estado de cada criterio; la suite completa pasa con `-W error` **sin tests saltados**; se hicieron mutaciones (una opción sin documentar, un código de advertencia sin documentar, un valor por defecto cambiado, un número de la reproducción cambiado, un archivo de más en el `sdist` o en el `wheel`, una versión desfasada, una dependencia de más) y cada una hace fallar al menos un test; el trabajo queda commiteado.

## Notas

- Orden de dependencia: T6.0 (licencia y cita) → T6.1 (metadatos) → T6.2 (versión) → T6.3 (dependencias) → T6.4 (construcción) → T6.5 a T6.9 (guía) → T6.10 (README) → T6.11 (instalación) → T6.12.
- T6.1 y T6.2 exigen reinstalar el entorno de desarrollo (`pip install -e .[dev]`), que descarga `build` y `setuptools`: el entorno tiene internet para `pip`.
- Los tests de la guía se escriben antes que cada sección (la sección no existe, el test falla) y la sección se escribe hasta que pasa.
- Si una tarea obliga a modificar un test existente, se corta y se consulta. Se espera que no haga falta: `--version` solo agrega una opción al analizador general.
- Las dudas abiertas de la clarificación (C9 a C14) no tienen tarea propia: se resuelven con las decisiones del plan (secciones 4 y 8).
