# Clarificación — Spec 006

Revisión crítica de `spec.md`. Esta fase **detecta** problemas; no los resuelve. Cada punto espera una decisión.

Severidad: **A** = condiciona el diseño o puede dar resultados mal fechados o mal asignados; **M** = ambigüedad que cambia resultados o impide testear; **B** = detalle.

## Lo que se verificó antes de revisar

- **Los códigos de advertencia se pueden comprobar de forma fiable.** Un recorrido del código fuente encuentra 26 códigos, todos escritos como texto literal en `Advertencia("…")` y ninguno armado dinámicamente. El test de RF-4 es viable.
- **Las opciones también.** El analizador define 9 opciones largas en `kvpi`, 8 en `mapa` y 22 en `analizar` (contando `--help` y `--depurar`); `--version` se sumaría al nivel general.
- **Las dependencias declaradas coinciden hoy con los imports** del paquete: `folium`, `numpy`, `pandas`, `pyproj`, `scipy` y `shapely`. RF-16 se cumple desde ya.
- **Los datos de referencia son chicos:** `tests/golden/` pesa 278 KB.
- **El equipo tiene Python 3.10 y 3.14** (`py -0`), así que el mínimo declarado (`>=3.10`) se puede probar de verdad. Hay internet para `pip`, pero `build` no está instalado en el entorno de desarrollo y `setuptools` tampoco.
- **Qué reproduce cada comando.** Con `--no-escalar-std` y `--estado-frio Deficiente`, el flujo reproduce el CSV publicado: 0 "Mantener" y 19 "Intervenir" (spec 003, criterio 4). Con el clima de INTA y `--campana 2024` da 16 "Mantener" y 19 "Intervenir". El FC es 1,2262 en los dos casos.

## Contradicciones e inconsistencias

- **C1 (A) — RESUELTO (opción A, 02/11/2026): la reproducción tiene dos partes rotuladas, "Reproducir lo publicado" (0 y 19, FC 1,2262, Student) y "Lo que agrega el programa" (16 y 19 con el clima de 2024, con nota sobre los 26 días interpolados); un test ejecuta las dos y la guía nunca presenta los 16 "Mantener" como resultado de la tesis (H4, RF-8, criterio 3).** ~~"Los resultados de la tesis" son dos cosas distintas y la spec las mezcla.~~ H4, RF-8 y el criterio 3 piden reproducir "los resultados de la tesis (16 'Mantener', 19 'Intervenir', FC 1,2262)". Pero el resultado publicado —el CSV `datos_plantas_completos.csv`— tiene **0 "Mantener" y 19 "Intervenir"**; los 16 "Mantener" salen del ajuste por frío con el clima de INTA, que es una función del programa nuevo y depende de 26 días interpolados. Una guía que presente 16/19 como "lo de la tesis" engaña a quien revise. Hay que separar dos reproducciones: la que reproduce lo publicado (con `--prueba-t student`, `--no-escalar-std` y `--estado-frio Deficiente`) y la que muestra lo que agrega el programa (con el clima), cada una con sus números y sus advertencias. (H4, RF-8, criterio 3)

## Vacíos

- **C2 (M) — RESUELTO (opción A, 02/11/2026): el `sdist` incluye los tests y los datos de `tests/golden/`; el `wheel` no, y la guía dice que la reproducción necesita el `sdist` o el repositorio (RF-8, RF-13).** ~~La reproducción no se puede hacer desde el paquete instalado.~~ RF-8 usa los datos de `tests/golden/`, y el `wheel` no los trae (RF-13). Quien instale con pip no tiene con qué reproducir. La guía debe decir que esa sección necesita el repositorio o el `sdist`, y hay que decidir si el `sdist` lleva los datos de referencia (278 KB, con las coordenadas del lote y el clima de INTA) o si la reproducción queda solo para quien clone el repositorio. (RF-8, RF-13, RF-14)
- **C3 (M) — Qué entra y qué no entra en el `sdist`.** RF-13 dice que el `sdist` incluye los tests, pero `setuptools` no incluye por defecto una carpeta `tests/` ni sus datos, y la carpeta de trabajo tiene archivos que **no** deben salir: `A872819 (2).xls` (datos de INTA), `mapa.html`, `resultados/`, `specs/`, `.venv`. Hace falta una lista explícita de inclusiones y una prueba de que lo demás no entra. (RF-13)
- **C4 (M) — Las versiones declaradas no están probadas, y la spec dice que no se afirme nada sin respaldo.** `requires-python = ">=3.10"` y `pandas>=2.0`, `numpy>=1.26`, `scipy>=1.11`, `shapely>=2.0`, `pyproj>=3.6`, `folium>=0.15` son números elegidos sin correr nada; todo se probó solo con Python 3.14 y las versiones más nuevas. Como hay un Python 3.10 en el equipo, se puede (a) declarar solo lo que se probó (Python 3.14 y las versiones actuales), (b) probar el piso real con una instalación mínima y declararlo, o (c) mantener lo declarado y decir en la guía que no se verificó. (RF-9, RF-11)
- **C5 (M) — Construir e instalar en un entorno limpio es lento y necesita red; choca con "sin tests saltados".** RF-13 y RF-14 piden construir y luego instalar el `wheel` en un entorno virtual nuevo, lo que descarga `setuptools`, `build` y todas las dependencias (pandas, scipy, shapely, pyproj, folium): cientos de megabytes y varios minutos. En la suite normal es inviable; marcarlo como opcional lo deja "saltado" y la validación exige cero saltados. Hay que decidir dónde vive esa prueba: en la suite (lenta), en una corrida aparte documentada en la validación, o con las dependencias ya instaladas (instalando el `wheel` sin dependencias en un entorno que ya las trae). (RF-13, RF-14, criterio 4)
- **C6 (M) — `--version` depende de cómo esté instalado.** Con `importlib.metadata`, un cambio de versión en `pyproject.toml` no se ve en una instalación editable hasta reinstalar (los metadatos quedan viejos), y ejecutar desde el código sin instalar no tiene metadatos. Falta decidir: qué muestra si no encuentra la versión (por ejemplo, `desconocida`), si el test compara contra `pyproject.toml` (que se lee con `tomllib`, disponible desde Python 3.11, no en 3.10) y que el entorno de desarrollo se reinstale tras cambiar la versión. (RF-15)
- **C7 (M) — No está decidido el número de versión.** El sandbox dice `0.0.1`, el repositorio original `1.1.0`, y la versión sale en `--version`, en los metadatos, en el nombre de los archivos y en la cita. Elegir una (por ejemplo `1.2.0`, siguiendo al repositorio original, o `1.0.0` para este programa) y decir qué significa. (Dudas abiertas, RF-11, RF-15)
- **C8 (M) — RF-1 pide "cómo citarlo" y no hay de dónde sacarlo.** El sandbox no tiene `CITATION.cff` (el del repositorio original cita la tesis y la versión 1.1.0). Hay que decidir si se copia adaptado al sandbox, si la guía remite al del repositorio original o si la cita queda fuera hasta publicar. (RF-1, dudas abiertas)

## Criterios y diseño

- **C9 (B) — `build-system` y "sin avisos".** `requires = ["setuptools>=68"]` y una licencia declarada como tabla producen avisos de obsolescencia con `setuptools` reciente; la forma sin avisos exige `setuptools>=77`, `license = "MIT"` y `license-files`. Se resuelve en el Plan, pero conviene fijarlo porque RF-13 exige "sin errores ni avisos". (RF-11, RF-13)
- **C10 (B) — `.gitignore` no cubre `dist/` ni `build/`.** Los archivos generados no se versionan (lo dice la spec) pero nada lo impide. (Entregables)
- **C11 (B) — El dialecto de la terminal.** La persona usa Windows y PowerShell; los ejemplos conviene escribirlos en una sola línea, con barras comunes en las rutas, para que valgan en PowerShell, `cmd` y `bash` sin continuaciones de línea. (RF-10)
- **C12 (B) — `mapa` pide internet para las teselas satelitales.** La guía tiene que decirlo y los ejemplos probados usan `--sin-fondo-satelital`. (RF-2, RF-9)
- **C13 (B) — Datos personales en los metadatos.** El autor sale del `CITATION.cff` (nombre y afiliación); no se debe agregar un correo y la URL del repositorio es privada, así que no sirve como enlace público. Decidir qué va y qué no. (RF-11)
- **C14 (B) — Cómo encuentra el test los comandos de la guía.** RF-8 dice que un test ejecuta los comandos de la guía, pero no cómo los reconoce (un bloque marcado, un encabezado) ni cómo reemplaza las rutas de ejemplo. Es de diseño, pero sin eso la guía y el test se acoplan de forma frágil. (RF-8)

## Resumen
- **1 hallazgo grave (A):** C1 (la reproducción de la tesis).
- **7 medios (M):** C2, C3, C4, C5, C6, C7 y C8.
- **6 menores (B):** C9, C10, C11, C12, C13 y C14.

El orden sugerido: **C1** (la guía no puede dar a entender que los 16 "Mantener" son de la tesis), **C2 y C3** (qué se entrega en cada archivo), **C4** (qué versiones se afirman), **C5** (dónde vive la prueba lenta), y después **C6, C7 y C8**.
