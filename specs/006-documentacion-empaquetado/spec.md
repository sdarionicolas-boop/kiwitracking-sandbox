# Spec 006 — Guía de uso y paquete instalable

Estado: BORRADOR (pendiente de clarificación)

## Contexto y objetivo
El sandbox ya hace todo el recorrido: `kvpi` agrega la serie de Earth Engine, `mapa` verifica la malla y da la huella, `analizar` corrige, clasifica y recomienda. Pero hoy **solo quien escribió el código sabe usarlo**: no hay README, no hay guía, la ayuda de la línea de comandos es lo único escrito, y el paquete se instala con `pip install -e .` desde la carpeta de trabajo, con una `description` que dice "Sandbox SDD" y una versión `0.0.1`.

Esta spec cierra eso para el público que realmente va a usar el programa: **un/a investigador/a que sabe abrir una terminal** y quiere instalarlo, correrlo con sus datos y reproducir los resultados de la tesis. Entrega dos cosas:
- **La documentación de uso** (`README.md` y `docs/uso.md`, en español), con un recorrido completo y ejemplos que se prueban con los datos de referencia, para que la guía no pueda quedar desactualizada sin que un test falle.
- **Un paquete instalable con pip**: metadatos completos, licencia MIT, y archivos `wheel` y `sdist` que se construyen y se instalan en un entorno limpio.

No cambia ningún cálculo ni ningún resultado. Salvo una opción nueva, `--version`, no cambia el comportamiento del programa.

## Usuarios / actores
- **Investigador/a** que instala el programa, lo corre con sus datos y reproduce la tesis.
- **Quien revisa la tesis** y quiere comprobar que los números salen de lo que dice la guía.

## Historias de usuario
- **H1.** Como investigador/a, quiero instalar el programa con un solo comando y saber qué necesito antes, para no depender de la carpeta del código.
- **H2.** Como investigador/a, quiero un recorrido completo (`kvpi` → `mapa` → `analizar`) con ejemplos que funcionan, para usarlo con mi propio lote.
- **H3.** Como investigador/a, quiero que cada opción, cada archivo de salida y cada advertencia estén explicados, para no tener que leer el código.
- **H4.** Como revisor/a, quiero reproducir con comandos exactos lo publicado en la tesis (FC 1,2262, 0 "Mantener" y 19 "Intervenir") y, por separado, ver qué agrega el programa con el clima, para no confundir lo uno con lo otro.
- **H5.** Como investigador/a, quiero saber qué versión tengo instalada (`kiwitracking --version`), para citarla.

## Entregables
- `README.md` en la raíz del sandbox.
- `docs/uso.md`.
- `LICENSE` (MIT) en la raíz.
- `pyproject.toml` completo.
- `kiwitracking --version` y `kiwitracking.__version__`.
- Los archivos `dist/kiwitracking-<versión>-py3-none-any.whl` y `dist/kiwitracking-<versión>.tar.gz`, generados (no versionados).

## Requisitos funcionales

**Documentación**
- **RF-1.** El `README.md` DEBE decir qué hace el programa y qué no, cómo instalarlo, un ejemplo mínimo de los tres comandos, dónde está la guía completa (`docs/uso.md`), la licencia y cómo citarlo.
- **RF-2.** `docs/uso.md` DEBE tener, en este orden: requisitos e instalación; el recorrido completo con los tres comandos; los formatos de los archivos de entrada; los archivos de salida; las advertencias; los códigos de salida; cómo reproducir los resultados de la tesis; cómo generar los paquetes; y los límites del programa.
- **RF-3.** TODAS las opciones de los comandos `kvpi`, `mapa` y `analizar` (las que define el analizador de argumentos) DEBEN estar nombradas en `docs/uso.md`, con una descripción y su valor por defecto cuando lo tienen. Un test compara la guía con el analizador.
- **RF-4.** TODOS los códigos de advertencia que el programa puede emitir DEBEN figurar en una tabla de `docs/uso.md` con su significado y qué hacer. Un test recorre el código fuente y falla si un código no está en la guía (o si la guía lista uno que ya no existe).
- **RF-5.** La guía DEBE explicar los códigos de salida 0, 1, 2 y 3.
- **RF-6.** La guía DEBE describir cada archivo de entrada (`serie`, `muestreo`, `plantas`, `malla`, `clima`): columnas obligatorias y opcionales, codificación UTF-8, punto decimal, y el sistema de coordenadas que se declara con `--crs-plantas`.
- **RF-7.** La guía DEBE describir cada archivo de salida: las columnas de `plantas.csv` y de `plantas_kvpi.csv`, la estructura de `resumen.json` y la de `advertencias.json`.
- **RF-8.** La sección de reproducción DEBE tener dos partes rotuladas, con los comandos exactos sobre los datos de `tests/golden/`: (1) **"Reproducir lo publicado"**: `mapa` y `analizar` con `--prueba-t student`, `--no-escalar-std` y `--estado-frio Deficiente`, que dan 53 plantas bajo malla y 106 fuera, FC 1,2262, valor p de 1,0e-26 (Student), 0 "Mantener" y 19 "Intervenir", y `KVPI_corregido`, ambientes y recomendaciones iguales a los de `datos_plantas_completos.csv`; (2) **"Lo que agrega el programa"**: `analizar` con el clima y `--campana 2024`, que da estado de frío "Óptimo" (1.128,8 h), 16 "Mantener" y 19 "Intervenir", con una nota que explica que esto NO es lo publicado y que 26 de los 123 días de ese invierno son interpolados. La sección DEBE decir que necesita los datos de `tests/golden/`, que están en el repositorio y en el `sdist` pero no en el `wheel` (quien instaló solo con pip debe bajar el `sdist` o clonar el repositorio). La guía NO DEBE presentar nunca los 16 "Mantener" como resultado de la tesis. Un test ejecuta los comandos de las dos partes y comprueba cada número que la guía afirma.
- **RF-9.** La guía DEBE decir qué NO hace el programa (la parte de Google Earth Engine, la elección de la prueba t de la tesis frente a la por defecto del programa, los días interpolados del clima y su efecto) y qué está verificado y qué no. NO DEBE afirmar nada que no tenga un test o un dato detrás.
- **RF-10.** Los ejemplos de comandos de la guía NO DEBEN llevar rutas del equipo de quien escribió la guía; usan rutas relativas y los nombres de archivo de los ejemplos.

**Empaquetado**
- **RF-11.** `pyproject.toml` DEBE declarar: nombre, versión, descripción (sin la palabra "Sandbox"), `readme`, licencia MIT, autor, `requires-python`, dependencias con versiones mínimas, clasificadores y palabras clave. Las versiones declaradas DEBEN ser las probadas: `requires-python = ">=3.14"` y, como piso de cada dependencia, la versión (hasta el menor) con que se corrió la suite completa: `pandas>=3.0`, `numpy>=2.5`, `scipy>=1.18`, `shapely>=2.2`, `pyproj>=3.8` y `folium>=0.20`. El clasificador de Python es solo 3.14. Un test comprueba que las versiones instaladas cumplen los pisos declarados, para que no puedan quedar por encima de lo probado. Ampliar el rango (Python 3.10 y versiones anteriores) queda para otra spec.
- **RF-12.** El repositorio DEBE tener el archivo `LICENSE` (MIT, el mismo texto del repositorio original) y el paquete construido DEBE incluirlo.
- **RF-13.** `python -m build` DEBE generar el `sdist` y el `wheel` sin errores ni avisos. El `wheel` DEBE contener solo el paquete `kiwitracking`, sus metadatos y la licencia (ni tests, ni specs, ni datos de referencia); el `sdist` DEBE incluir exactamente esta lista (declarada en un `MANIFEST.in` como lista de inclusión): `kiwitracking/`, `tests/` (los `.py` y los datos de `tests/golden/`), `docs/uso.md`, `README.md`, `LICENSE` y `pyproject.toml`, más los metadatos que genera la herramienta. NO DEBE contener nada más: ni `specs/`, ni `AGENTS.md`, `CLAUDE.md` o `docs/constitution.md`, ni `mapa.html`, ni `resultados/`, ni archivos `.xls`, ni `.venv`, `dist/` o `build/`. Un test abre el `sdist` construido y compara su contenido con la lista.
- **RF-14.** Instalar el `wheel` en un entorno virtual limpio (con sus dependencias, descargadas de internet) DEBE crear el comando `kiwitracking`; `kiwitracking --help`, `python -m kiwitracking --help` y el ejemplo mínimo del README DEBEN funcionar desde una carpeta que no sea la del código. Esta comprobación la hace un script (`scripts/probar_instalacion.py`) que se corre aparte de la suite, porque tarda más de un minuto y necesita red (medido: 52 s y 326 MB solo para instalar las dependencias); `validacion.md` DEBE registrar la fecha, la versión y el resultado de esa corrida. Los tests de la suite, que no necesitan entorno nuevo, construyen el `wheel` y el `sdist` e inspeccionan su contenido (RF-13).
- **RF-15.** La versión DEBE declararse en un solo lugar (`pyproject.toml`). `kiwitracking --version` DEBE imprimir `kiwitracking <versión>` con código de salida 0, y `kiwitracking.__version__` DEBE ser la misma versión.
- **RF-16.** Cada módulo de terceros que el paquete importa DEBE figurar en las dependencias de `pyproject.toml`, y cada dependencia declarada DEBE usarse. Un test lo comprueba.

## Requisitos no funcionales
- Todo en español, igual que el resto del sandbox; los comandos y los nombres de archivo van en bloques de código.
- La documentación NO DEBE duplicar los valores por defecto de forma que un cambio en el código la desactualice sin aviso: las pruebas de RF-3 los comparan con el analizador.
- El empaquetado no agrega dependencias de ejecución (constitución #1); `build` es una herramienta de desarrollo y va en las dependencias opcionales `dev`.
- No se publica nada en ningún índice de paquetes ni se sube nada: la construcción es local.

## Casos límite
- Una opción que se agrega al analizador sin documentar: el test de RF-3 falla.
- Un código de advertencia nuevo sin documentar: el test de RF-4 falla.
- Un ejemplo de la guía cuyo resultado cambia: el test de RF-8 falla.
- El `wheel` se instala en un entorno sin los datos de `tests/golden/`: el comando y el ejemplo mínimo siguen funcionando con archivos que trae el usuario.
- Un entorno sin acceso a internet: la construcción necesita `setuptools` y `build` (`build` va en las dependencias opcionales `dev`); sin red y sin ellos instalados, ni la construcción ni la prueba de instalación pueden correr.

## Fuera de alcance
- Un ejecutable para Windows (PyInstaller) o un instalador.
- Publicar en PyPI, crear un repositorio público o configurar integración continua.
- Una guía para técnicos de campo sin experiencia en terminal.
- Cambiar el comportamiento o los resultados del programa, salvo agregar `--version`.
- Documentar la parte de Google Earth Engine (los notebooks del repositorio original).
- Editar `docs/` del repositorio original (la corrección de `metodologia.md` queda como texto para aplicar a mano).

## Criterios de finalización
1. Todos los tests `RF-n` pasan, con avisos tratados como errores.
2. **La guía no se desactualiza:** los tests de RF-3, RF-4 y RF-5 comparan la guía con el analizador de argumentos, el código fuente y los códigos de salida.
3. **Se reproduce la tesis, y se distingue de lo nuevo:** los comandos de las dos partes de la sección de reproducción, ejecutados por un test, dan los números que la guía afirma, y la parte 2 aclara que no es lo publicado.
4. **Se construye y se instala:** `python -m build` genera el `wheel` y el `sdist`; el `wheel` se instala en un entorno virtual limpio, crea el comando `kiwitracking`, y `--version`, `--help` y el ejemplo mínimo funcionan desde otra carpeta.
5. El contenido del `wheel` y del `sdist` es el de RF-13.
6. Cada requisito tiene al menos un test asociado (fase de Validación).

## Dudas abiertas
- **[NECESITA ACLARACIÓN]** Número de versión: el sandbox está en `0.0.1`; el repositorio original en `1.1.0` (`CITATION.cff`). Falta decidir con cuál sale el paquete.
- *Resuelta el 02/11/2026 (C4):* se declara solo lo probado (Python 3.14 y las versiones actuales de las dependencias); ampliar el rango queda para otra spec.
- *Resuelta el 02/11/2026 (C5):* la construcción y la inspección del contenido van en la suite; la instalación en un entorno limpio es un script aparte, registrado en `validacion.md`.
- **[NECESITA ACLARACIÓN]** URL del proyecto en los metadatos: el repositorio del sandbox es privado; una URL que no abre no sirve a quien instale.
- **[NECESITA ACLARACIÓN]** Cómo citar: el `CITATION.cff` del repositorio original apunta a la tesis; el sandbox no tiene uno.
- **[NECESITA ACLARACIÓN]** La prueba t por defecto del programa (Welch) difiere de la de la tesis (Student): la guía lo explica y da `--prueba-t student`, pero conviene decidir si el ejemplo de reproducción usa Student para que el valor p coincida con el de la tesis.

## Historial de cambios
- **Clarificación (02/11/2026).** Se resolvió C5: dos pruebas, una rápida en la suite (construir e inspeccionar el `wheel` y el `sdist`) y una lenta aparte (`scripts/probar_instalacion.py`, instalación en un entorno limpio), cuyo resultado se registra en `validacion.md` (RF-13, RF-14).
- **Clarificación (02/11/2026).** Se resolvió C4: se declaran solo las versiones probadas (`requires-python >=3.14` y pisos en las versiones con que se corrió la suite), y un test comprueba que las instaladas los cumplen (RF-11).
- **Clarificación (02/11/2026).** Se resolvió C3: el `sdist` lleva una lista explícita de inclusión (`MANIFEST.in`) y un test compara su contenido con ella; nada fuera de la lista viaja por omisión (RF-13).
- **Clarificación (02/11/2026).** Se resolvió C2: el `sdist` lleva los tests y los datos de `tests/golden/` para poder reproducir; el `wheel` no, y la guía lo dice (RF-8, RF-13).
- **Clarificación (02/11/2026).** Se resolvió C1: la reproducción tiene dos partes rotuladas, "Reproducir lo publicado" (0 y 19, FC 1,2262, Student) y "Lo que agrega el programa" (16 y 19 con el clima de 2024); la guía nunca presenta los 16 "Mantener" como resultado de la tesis (H4, RF-8, criterio 3).
- **Borrador (02/11/2026).** Alcance acordado en la entrevista: público investigador/a que reproduce y reutiliza, paquete instalable con pip (sin ejecutable), y la guía en `README.md` y `docs/uso.md` dentro del sandbox, con ejemplos probados contra los datos de referencia.
