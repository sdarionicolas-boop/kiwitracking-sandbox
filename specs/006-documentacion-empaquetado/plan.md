# Plan — Spec 006

Estado: BORRADOR. Sin código. Lee: `docs/constitution.md`, `spec.md` (RF-1 a RF-17) y `clarificacion.md`. Los hallazgos menores (C9 a C14) se resuelven con las decisiones de las secciones 4 y 8; se pueden cambiar.

## 1. Idea general

Dos entregas que se apoyan en tests para no desactualizarse: **una guía cuyo contenido se compara con el código** (opciones, valores por defecto, códigos de advertencia, números de la reproducción) y **un paquete cuya construcción se inspecciona**. **No hacen falta dependencias de ejecución nuevas** (constitución #1); `build` va en las dependencias opcionales `dev`.

```
README.md ──┐
docs/uso.md ┴─► tests/test_docs.py ........ opciones, valores por defecto, códigos, estructura (RF-2 a RF-7, RF-9, RF-10)
              └► tests/test_docs_ejemplos.py ... ejecuta los bloques marcados con main(argv) (RF-8, ejemplo mínimo del README)

pyproject.toml, LICENSE, CITATION.cff, MANIFEST.in
              └► tests/test_pyproject.py ..... metadatos, versiones, imports contra dependencias, cita (RF-11, RF-12, RF-16, RF-17)
              └► tests/test_empaquetado.py ... python -m build --no-isolation; contenido del wheel y del sdist (RF-13)
kiwitracking/__init__.py + cli.py
              └► tests/test_version.py ....... __version__, --version, valor de reserva (RF-15)

scripts/probar_instalacion.py ... entorno limpio + wheel + dependencias + comandos (RF-14)   [corrida aparte, se registra en validacion.md]
```

La guía se escribe **después** de los tests que la comparan: primero el test (que falla porque la guía no existe), después el texto que lo hace pasar.

## 2. Módulos y archivos

| Archivo | Qué es | RF que cubre |
|---|---|---|
| `kiwitracking/__init__.py` (se amplía) | `__version__`, leída de los metadatos instalados con valor de reserva `desconocida` | RF-15 |
| `kiwitracking/cli.py` (se amplía) | Opción general `--version` (`argparse` `action="version"`), impresa como `kiwitracking <versión>` | RF-15 |
| `pyproject.toml` (se reescribe) | Metadatos completos, versión `1.2.0`, `setuptools>=77`, dependencias `dev` con `build` | RF-11 |
| `LICENSE` (nuevo) | MIT, mismo texto del repositorio original | RF-12 |
| `CITATION.cff` (nuevo) | Cita propia, versión `1.2.0`, sin correo | RF-17 |
| `MANIFEST.in` (nuevo) | Lista de inclusión del `sdist` | RF-13 |
| `.gitignore` (se amplía) | `dist/` y `build/`; se actualiza el comentario sobre los `.xls` de INTA | Entregables |
| `README.md` (nuevo) | Qué es, instalación, ejemplo mínimo, cómo citar, licencia | RF-1, RF-10 |
| `docs/uso.md` (nuevo) | La guía completa | RF-2 a RF-10 |
| `scripts/probar_instalacion.py` (nuevo) | Prueba de instalación en un entorno limpio | RF-14 |

## 3. Estructura de la guía

`docs/uso.md`, en este orden fijo (RF-2; un test comprueba los encabezados):

1. Requisitos e instalación
2. Recorrido completo (`kvpi` → `mapa` → `analizar`, con las opciones de cada comando)
3. Formatos de los archivos de entrada
4. Archivos de salida
5. Advertencias
6. Códigos de salida
7. Reproducir los resultados de la tesis (dos partes: *Reproducir lo publicado* y *Lo que agrega el programa*)
8. Generar los paquetes
9. Límites del programa

Convenciones que los tests aprovechan:
- Cada opción se documenta con una línea que empieza por `` - `--opcion` `` y, si tiene valor por defecto, termina en `(por defecto: <valor>)`.
- La tabla de advertencias tiene una fila por código con el código entre comillas invertidas: `` | `SIN_DESVIO` | … ``.
- La tabla de códigos de salida tiene las filas `| 0 |`, `| 1 |`, `| 2 |` y `| 3 |`.
- Los comandos que se ejecutan en los tests van en bloques ```` ```bash ```` precedidos de un comentario HTML `<!-- prueba: nombre -->`.

## 4. Decisiones técnicas

| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D1 | `--version` usa `argparse` (`action="version"`); como `main` ya captura `SystemExit`, devuelve 0 | Un subcomando `version` | Es lo estándar y no cambia la forma de los otros comandos (RF-15) |
| D2 | `__version__` se lee con `importlib.metadata.version("kiwitracking")`; si no hay metadatos, `desconocida` | Escribir el número en el código | Una sola fuente de verdad (C6) |
| D3 | Los valores por defecto de la guía se comparan con los del código: `inspect.signature` de `analizar`, `ParametrosClima` y `ejecutar_kvpi`; los números se escriben con punto (así se tipean en la línea de comandos) | Copiar los valores en el test | Una sola definición (constitución #7); un cambio en el código hace fallar la guía |
| D4 | Los códigos de advertencia se extraen con `ast`: todo `Advertencia("CODIGO", …)` de `kiwitracking/*.py` | Expresión regular sobre el texto | Se verificó que hay 26 y que todos son literales; el recorrido del árbol no se confunde con comentarios |
| D5 | Los bloques de la guía que se ejecutan se marcan con `<!-- prueba: … -->`; el test los ejecuta con `main(argv)` en una carpeta temporal que contiene una copia de `tests/golden/` | Extraer todos los bloques `bash` | Sin marca, un comando de ejemplo de relleno podría romper un test sin motivo; la marca hace explícito qué se promete (C14) |
| D6 | Los comandos de la guía usan el marcador `HUELLA`; el test lo reemplaza por la huella que imprimió el `mapa` anterior | Escribir el valor `c4e55ae105c6` en el comando | La guía enseña a copiar la huella de la pantalla; el valor esperado se afirma en la tabla de resultados, no en el comando |
| D7 | Los números que la guía afirma para la reproducción están en una tabla; el test tiene los valores esperados y comprueba que **cada uno aparece en la guía** y que el comando lo produce | Comprobar solo el comando | La guía y el test no pueden discrepar (RF-8) |
| D8 | El `wheel` y el `sdist` se construyen con `python -m build --no-isolation` en una carpeta temporal; `build` y `setuptools>=77` están en el entorno de desarrollo (extra `dev`) | Construcción aislada en el test | Sin descargar nada: la suite no depende de la red; la construcción aislada la ejercita el script (C5) |
| D9 | `pyproject.toml`: `license = "MIT"` (SPDX) y `license-files = ["LICENSE"]`, con `setuptools>=77` | Licencia como tabla | Sin avisos de obsolescencia (C9, RF-13) |
| D10 | `MANIFEST.in` con solo líneas de inclusión: `README.md`, `LICENSE`, `CITATION.cff`, `docs/uso.md` y `recursive-include tests *.py *.csv *.geojson *.txt`; el test compara el contenido real del `sdist` con la lista permitida | Excluir lo que sobra | Lo que no se nombra no viaja (C3) |
| D11 | El `wheel` solo trae el paquete `kiwitracking`, sus metadatos y `LICENSE`; el test compara la lista exacta de archivos | Revisar solo que no haya `tests/` | Detecta cualquier archivo inesperado |
| D12 | Sin `project.urls` y sin correo del autor; sin clasificador de sistema operativo (solo se probó en Windows 11; la guía lo dice) | URL del repositorio privado, `OS Independent` | Nada sin respaldo y sin datos personales (C13, RF-9) |
| D13 | Los ejemplos de la guía van en una sola línea, con barras comunes en las rutas y con `--sin-fondo-satelital` en los de `mapa` | Continuaciones de línea; teselas | Valen en PowerShell, `cmd` y `bash`; las pruebas no usan la red (C11, C12) |
| D14 | La prueba de dependencias contra imports usa `sys.stdlib_module_names`; la de versiones compara solo (mayor, menor) con `importlib.metadata`, sin agregar `packaging` | Agregar `packaging` | Constitución #1 |
| D15 | `scripts/probar_instalacion.py` crea el entorno con `venv`, instala el `wheel` desde `dist/` (con dependencias), corre los comandos y el ejemplo mínimo desde una carpeta nueva y devuelve un código de salida distinto de 0 si algo falla | Un test más de la suite | Tarda más de un minuto y necesita red (C5) |

## 5. Estrategia de pruebas

Las mismas reglas: cada RF tiene un test que lleva su número (`test_rfN_...`), el test se escribe primero y se ve fallar, y al cerrar cada grupo se hacen mutaciones. Los de la guía y el paquete usan los archivos reales del sandbox.

| Archivo de tests | Qué prueba | Datos |
|---|---|---|
| `test_version.py` | RF-15: `__version__` contra `pyproject.toml`, `--version` (salida y código 0), valor de reserva sin metadatos | El paquete instalado y `pyproject.toml` |
| `test_pyproject.py` | RF-11, RF-12, RF-16 y RF-17: campos de `pyproject.toml`, versiones instaladas contra los pisos, imports contra dependencias, `LICENSE`, `CITATION.cff` | Archivos del sandbox |
| `test_empaquetado.py` | RF-13: construcción sin errores ni avisos, nombres de los archivos, contenido exacto del `wheel` y del `sdist`, punto de entrada | Construcción real en una carpeta temporal |
| `test_docs.py` | RF-1 a RF-7, RF-9 y RF-10: README y guía contra el analizador, los valores por defecto, los códigos de advertencia y de salida, los encabezados en orden, las rutas personales | `README.md`, `docs/uso.md` y el código |
| `test_docs_ejemplos.py` | RF-8 y el ejemplo mínimo del README: los bloques marcados se ejecutan y dan los números afirmados | Copia de `tests/golden/` en una carpeta temporal |

## 6. Riesgos

1. **Acoplamiento entre la guía y los tests.** Las convenciones de la sección 3 son rígidas a propósito; un texto mal formateado hace fallar un test. Se mitiga con mensajes de error que dicen exactamente qué línea falta.
2. **`build` y `setuptools>=77` en el entorno de desarrollo.** Hay que instalarlos (`pip install -e .[dev]`) una vez; sin ellos `test_empaquetado.py` no puede correr, y la tarea correspondiente lo dice.
3. **`--version` y la instalación editable.** Cambiar la versión de `pyproject.toml` exige reinstalar (C6); el test lo avisa.
4. **Contenido de la guía.** Es lo más largo de escribir y lo que más fácil queda impreciso. Todo número, opción y código que afirme está respaldado por un test; lo demás (explicaciones) se revisa a mano en la validación.
5. **El `sdist` lleva datos del lote.** Decidido en C2; la guía lo dice.
6. **Ejecutar comandos de la guía en los tests.** El `mapa` genera un HTML por corrida; los tests usan `--sin-fondo-satelital` y una carpeta temporal.

## 7. Cobertura de requisitos

| RF | Archivo(s) | Test |
|---|---|---|
| 1, 10 | `README.md` | `test_docs` |
| 2, 9 | `docs/uso.md` | `test_docs` |
| 3 | `docs/uso.md`, `cli` | `test_docs` |
| 4, 5 | `docs/uso.md` | `test_docs` |
| 6, 7 | `docs/uso.md` | `test_docs` (campos), `test_docs_ejemplos` |
| 8 | `docs/uso.md` | `test_docs_ejemplos`, `test_docs` |
| 11, 16 | `pyproject.toml` | `test_pyproject` |
| 12, 17 | `LICENSE`, `CITATION.cff` | `test_pyproject` |
| 13 | `pyproject.toml`, `MANIFEST.in` | `test_empaquetado` |
| 14 | `scripts/probar_instalacion.py` | corrida aparte, registrada en `validacion.md` |
| 15 | `__init__`, `cli` | `test_version` |

## 8. Decisiones provisionales sobre los hallazgos menores

Todas siguen como dudas abiertas y se pueden cambiar:

- **C9.** `build-system` con `setuptools>=77`, licencia como texto SPDX y `license-files` (D9).
- **C10.** `.gitignore` suma `dist/` y `build/`; el comentario sobre los `.xls` de INTA deja de decir "condiciones de uso sin verificar" (se informó que no tienen condiciones declaradas).
- **C11.** Los ejemplos van en una línea y con barras comunes (D13).
- **C12.** La guía dice que `mapa` necesita internet para el fondo satelital; los ejemplos usan `--sin-fondo-satelital` (D13).
- **C13.** Sin correo ni URL en los metadatos (D12).
- **C14.** Los bloques ejecutables se marcan con un comentario HTML (D5).
- **Sistema operativo.** La guía dice que se probó en Windows 11 con Python 3.14; no afirma nada de otros sistemas.
- **Idioma de los metadatos.** `description` y `keywords` en español, con palabras clave en inglés para los buscadores.
