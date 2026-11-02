# Validación — Spec 004

Fecha de la corrida: 02/11/2026. Comando: `.venv\Scripts\python -m pytest -W error -rs` → **1.230 tests, 1.230 pasan, 0 avisos, 0 saltados** (1.004 de las specs 001 a 003 y 226 de la spec 004).

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`; cuenta cada caso de los tests parametrizados). Los números salen de los nombres de los tests, no de una lectura semántica.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 8 | OK | test_kvpi_validacion | Columnas obligatorias (`id`, `KVPI`, `campaña` o `campana`) y la que falta nombrada; serie vacía; `campaña` y `campana` a la vez |
| 2 | 3 | OK | test_kvpi_validacion | `id` o campaña vacíos: error con la cantidad (singular y plural) |
| 3 | 12 | OK | test_kvpi_validacion | Texto no numérico con ejemplo (incluido `-`), coma decimal como causa probable, infinitos (también el texto `inf`), y la celda en blanco y los textos ausentes de `pandas` como vacío sin aviso |
| 4 | 7 | OK | test_kvpi_validacion | Repetidos iguales (también dos vacíos) → una sola con `KVPI_DUPLICADO`; distintos (también número contra vacío) → error con hasta 10 pares y cuántos más hay |
| 5 | 4 | OK | test_kvpi_validacion | Etiquetas sin espacios al inicio ni al final; no se interpretan ni se unifican formatos distintos; etiquetas numéricas como texto |
| 6 | 3 | OK | test_kvpi_validacion | Mismo resultado al barajar filas, con columnas extra y en otro orden; la tabla de entrada no se modifica |
| 7 | 4 | OK | test_kvpi_calculo | `n_campanas` (solo campañas con dato) y `KVPI_mean`; planta sin ningún dato con promedio vacío y `n_campanas` 0 |
| 8 | 5 | OK | test_kvpi_calculo | Desvío muestral con divisor n−1 (a mano y contra `numpy`); `min_campanas` por defecto 2 y mayor que 2; el promedio se conserva |
| 9 | 3 | OK | test_kvpi_calculo | `KVPI_cv` = desvío / promedio; vacío con promedio 0; conserva el signo con promedio negativo |
| 10 | 12 | OK | test_kvpi_calculo | `min_campanas` menor que 2, decimal, texto, `None` o booleano → error con los valores permitidos; enteros de 2 en adelante (incluidos los de `numpy`) |
| 11 | 5 | OK | test_kvpi_calculo | `PLANTAS_CON_MENOS_CAMPANAS` contra las etiquetas encontradas (también la campaña con todo vacío), con cantidad y rango; no sale con una sola campaña |
| 12 | 4 | OK | test_kvpi_calculo | `SIN_DESVIO` con la cantidad y el umbral real de `min_campanas` |
| 13 | 18 | OK | test_kvpi_union | Columnas y orden, orden del muestreo, `id` como texto, `PLANTAS_SIN_COORDENADAS` (también `X` o `Y` vacías), `PLANTAS_SIN_SERIE` con hasta 10 `id` y la frase de la huella, ninguna en común → error, orden de las advertencias |
| 14 | 14 | OK | test_kvpi_union | Columnas obligatorias del muestreo, muestreo vacío, `id` vacío, coordenadas con texto, `id` repetidos (iguales → `MUESTREO_DUPLICADO`; distintos → error con hasta 10 `id`) |
| 15 | 17 | OK | test_kvpi_flujo, test_kvpi_cli | Lectura con la spec 001 (BOM, UTF-8), archivo inexistente, carpeta o vacío nombrados, parámetros validados antes de leer, rutas con espacios y tildes |
| 16 | 18 | OK | test_kvpi_salida, test_kvpi_cli | UTF-8 sin BOM, `\n`, números completos, celdas vacías, no sobrescribe sin `--sobrescribir`, archivo temporal con reemplazo (no queda un archivo a medio escribir), carpeta creada y borrada si falla |
| 17 | 9 | OK | test_kvpi_cli | Pantalla: plantas, campañas con cobertura, plantas por cantidad de campañas, advertencias, ruta del archivo y la pista para `--plantas` de `mapa` y `analizar` |
| 18 | 18 | OK | test_kvpi_cli | Opciones y ayuda en español, códigos 0, 1, 2 y 3, parámetros que llegan al flujo sin copiar los valores por defecto, en un proceso aparte y con la consola en ASCII |
| 19 | 5 | OK | test_kvpi_cli, test_kvpi_flujo, test_kvpi_salida | Los archivos de entrada no cambian (se comparan los bytes) y un error no deja archivos de salida |
| 20 | 11 | OK | test_kvpi_cobertura | Plantas con dato y proporción por campaña, campaña sin datos con 0, `total_plantas` y su validación |
| 21 | 16 | OK | test_kvpi_cobertura | `CAMPANA_CON_POCOS_DATOS` con nombre, cantidad y proporción; justo en el mínimo no avisa; mínimo fuera de 0 a 1 → error |
| 22 | 12 | OK | test_kvpi_cobertura | Campañas esperadas: faltante o sobrante → error que las nombra; lista vacía, repetida, con una etiqueta vacía o un texto en vez de una lista → error; sin lista una campaña ausente no se detecta |

**Ninguno de los 22 RF queda sin test.** Los más delgados son RF-2 y RF-6 (3 tests cada uno); alcanzan para su comportamiento. Los 18 tests sin número de RF son los de datos de referencia (`test_kvpi_datos`, 3), los de la serie real (`test_kvpi_golden`, 8) y algunos de comportamiento general del núcleo (orden de las advertencias, independencia del orden de filas, no modificar la entrada).

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests `RF-n` pasan, con avisos como errores | **Cumplido** | 1.230/1.230 con `-W error` |
| 2 | Serie sintética: `KVPI_mean`, `KVPI_std`, `KVPI_cv` y `n_campanas` coinciden con lo calculado a mano | **Cumplido** | `test_kvpi_calculo`: plantas armadas a mano con campañas faltantes, una sola campaña, todas vacías y promedio 0 |
| 3 | Serie real: `KVPI_mean` y `KVPI_std` de las 159 plantas coinciden con lo publicado (menos de 1e-12); sin repetidos ni vacíos | **Cumplido** | `test_kvpi_golden` (núcleo y comando) y `test_kvpi_datos`; las 159 plantas tienen las 6 campañas y no hay advertencias |
| 4 | `kvpi`, `mapa` y `analizar` dan 16 "Mantener" y 19 "Intervenir" con el frío de 2024 | **Cumplido** | `test_kvpi_golden`: misma huella que el lote publicado, estado "Óptimo" de 2024, y con `--no-escalar-std` y `--estado-frio Deficiente` el resultado es igual al de `analizar` sobre el CSV publicado |
| 5 | El comando `kvpi` da código 1 con mensaje claro y sin traza ante cada error de entrada conocido, y no deja archivos a medio escribir | **Cumplido** | `test_kvpi_cli` (error de datos, archivo inexistente, ninguna planta en común, campañas esperadas, parámetros fuera de rango) y `test_kvpi_salida` (fallo simulado) |
| 6 | Cada requisito tiene al menos un test | **Cumplido** | Sección 1 (22 RF) |

## 3. Mutaciones

Cada cambio se aplicó con un script que verifica que el patrón existe, se corrieron todos los tests de la spec 004 con `-W error` y se restauró el código.

| Mutación | Resultado |
|---|---|
| Divisor del desvío (n−1 → n) | Detectada |
| Repetido igual: el vacío deja de ser un valor más | Detectada |
| Umbral de `min_campanas` (< → <=) | Detectada |
| Cobertura contra el total equivocado | Detectada |
| Orden de las columnas de la unión | Detectada |
| `PLANTAS_SIN_SERIE` sin la frase de la huella | Detectada |
| Promedio vacío con menos de `min_campanas` | Detectada |
| Sin comparar con las campañas esperadas | Detectada |
| Cobertura por debajo del mínimo (< → <=) | Detectada |
| Parámetros validados después de leer los archivos | Detectada |
| Escritura directa al destino en vez de archivo temporal | Detectada |
| Valores por defecto copiados en la línea de comandos | Detectada |

Durante T4.1 a T4.9 se hicieron además mutaciones por tarea (más de 120 en total). Sobrevivieron algunas equivalentes y se anotaron en cada tarea: ordenar por `id` antes de agrupar (ya lo hace la validación), el chequeo de booleano en `min_campanas` (se quitó por redundante), `nunique` frente a `count` (no hay repetidos después de la validación), la inversión de una lista de avisos de un solo elemento y la lectura con `pd.read_csv` frente a `leer_csv` ante el BOM (la diferencia real la detecta un test con un archivo en cp1252).

Una mutación hizo que un test escribiera `plantas_kvpi.csv` en el directorio del proyecto, porque no indicaba `--salida`. Se agregó al archivo de tests de la línea de comandos un cambio automático de carpeta de trabajo, para que ningún test pueda ensuciar el proyecto.

## 4. Correcciones a la spec durante la implementación

Dos puntos de la spec se precisaron al escribir el código, siempre con la spec primero:
- **RF-13 y RF-14 (T4.5):** un muestreo vacío, con `id` vacío o con `X`/`Y` no numéricas es un error; una planta con `X` o `Y` vacías cuenta como sin coordenadas; el aviso de repetidos del muestreo se llama `MUESTREO_DUPLICADO`; `PLANTAS_SIN_COORDENADAS` nombra hasta 10 `id`.
- **Casos límite (T4.6):** si la serie trae plantas que no están en el muestreo, la cobertura de una campaña puede pasar de 100 %, porque se mide sobre la serie y el total son las plantas del muestreo.

## 5. Limitaciones y dudas abiertas

- **Procedencia incompleta de la serie.** `AGENTS.md` deja pendiente el proyecto de Earth Engine y la versión de las imágenes con que se exportó `kvpi_serie.csv`. Sin eso, una diferencia con lo publicado no se puede explicar.
- **Filas que no existen.** Sigue sin confirmarse que Earth Engine omita la fila de un punto sin píxel válido (en vez de exportar `KVPI` vacío). La serie real tiene las 954 filas (159 × 6) y no lo permite verificar; la cobertura por campaña y `--campanas` son la defensa.
- **Hallazgos menores de la clarificación (C8, C9, C11 y C12).** Siguen como dudas abiertas con la decisión provisional del plan: las columnas extra del muestreo pasan al resultado, `--min-campanas abc` da código 2, el criterio 4 se superpone con la spec 003 y la serie real entró a `tests/golden/` con una procedencia a completar.
- **`id` con decimal.** Un `4.0` en un archivo y un `4` en el otro no coinciden; la advertencia `PLANTAS_SIN_SERIE` lo deja a la vista pero no se normaliza.
- **Valores de `KVPI`.** No se valida el rango (un valor absurdo entra al promedio) y el CV de un promedio negativo conserva el signo.
- **Cobertura mayor que 100 %.** Ocurre si la serie trae plantas fuera del muestreo; es una señal, no un error.
- **Permisos del archivo de salida.** El archivo se crea a través de un temporal con los permisos restrictivos de Python (solo el usuario). En Windows no importa; en Linux convendría revisarlo.
- **Pasos de Earth Engine.** La mediana por campaña, la máscara de nubes, el rango de EVI y las ventanas de campaña (junio en dos campañas) quedan fuera de esta spec y siguen como dudas abiertas de la metodología.
- **Mensajes de `argparse`.** Los errores de uso (código 2) usan los textos de `argparse` y pueden salir en inglés, como en la spec 003.
