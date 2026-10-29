# Clarificación — Spec 004

Revisión crítica de `spec.md`. Esta fase **detecta** problemas; no los resuelve. Cada punto espera una decisión.

Severidad: **A** = condiciona el diseño o puede dar resultados mal fechados o mal asignados; **M** = ambigüedad que cambia resultados o impide testear; **B** = detalle.

## Lo que se verificó antes de revisar

- **El cálculo publicado sale del notebook 03, no del 01.** En `03_IVP_Kiwi_Producto_Final.ipynb` (celda 6) los valores se obtienen con `df_kvpi.groupby('id')['KVPI'].agg(['mean', 'std', 'count'])`, y esa es la regla que produjo `datos_plantas_completos.csv`. Coincide con la spec: promedio, desvío muestral (n−1, el de `pandas`) y cantidad de campañas con dato (`count` no cuenta los vacíos). El notebook 01 hace lo mismo con `pivot_table` y agrega el CV, que el 03 no usa.
- **El muestreo de referencia coincide con el lote publicado.** `DEM_MIRAMAR/muestreo_sistematico.csv` tiene 159 plantas, `id` únicos, los mismos 159 `id` que el lote de referencia y `X` e `Y` idénticos (diferencia 0). Trae además columnas `left`, `top`, `right`, `bottom`, `row_index` y `col_index`.
- **El análisis de la spec 001 tolera lo que `kvpi` va a producir.** Una planta con `KVPI_std` vacío entra con estabilidad vacía y recomendación "Observar"; una con `KVPI_mean` vacío se excluye con el aviso `PLANTAS_EXCLUIDAS`. Ninguna da error.

## Contradicciones e inconsistencias

- **C1 (M) — RESUELTO (opción A, 29/10/2026): la referencia es el notebook 03; RF-4 se mantiene (iguales: una sola con aviso; distintos: error) y la spec la declara deliberadamente más estricta que los dos notebooks. La serie real no tiene repetidos y un test lo comprueba.** ~~La spec cita el notebook 01 como origen, y los dos notebooks tratan distinto los repetidos.~~ Con filas repetidas del mismo `id` y la misma campaña, el notebook 01 (`pivot_table`) las promedia sin avisar, y el 03 (`groupby`) las cuenta como campañas separadas: suben `n_campanas` y entran al promedio y al desvío. RF-4 no hace ninguna de las dos cosas (iguales: una sola con aviso; distintas: error). Si la serie real exportada tuviera repetidos, el valor publicado (del 03) no se podría reproducir y `kvpi` se detendría. Falta decir que la referencia es el notebook 03, que la regla de repetidos es deliberadamente más estricta, y qué se hace si la serie real los trae. (Contexto, RF-4, criterio 3)
- **C2 (M) — `--plantas` significa cosas distintas en `kvpi` y en los otros comandos.** En `mapa` y `analizar`, `--plantas` es el CSV que ya trae `KVPI_mean` y `KVPI_std`; en `kvpi`, es el muestreo con coordenadas y sin KVPI. La secuencia `kvpi --plantas muestreo.csv` y después `mapa --plantas plantas_kvpi.csv` se presta a pasar el archivo equivocado. (Entradas, RF-15)

## Vacíos

- **C3 (A) — RESUELTO (opción B, 24/10/2026): cobertura por campaña siempre calculada y mostrada, advertencia `CAMPANA_CON_POCOS_DATOS` por debajo de 0,5 (parámetro), y lista opcional de campañas esperadas que da error si falta o sobra alguna (RF-11, RF-17, RF-20 a RF-22). Sin la lista, una campaña ausente por completo no se puede detectar y la spec lo dice.** ~~No hay una referencia de cuántas campañas se esperan, y una campaña entera puede faltar sin que nadie lo note.~~ RF-11 compara con "el máximo observado". Pero en la exportación de Earth Engine (`sampleRegions`), un punto sin píxel válido en una campaña normalmente no genera una fila con `KVPI` vacío: la fila directamente no existe (a verificar con la serie real). Entonces una campaña sin ningún dato válido, por ejemplo un año con nubes en todo el lote, no aparece en las etiquetas, `KVPI_mean` se promedia sobre 5 campañas en vez de 6 y ninguna advertencia salta, porque todas las plantas tienen el mismo máximo. El comando muestra las campañas encontradas (RF-17), pero solo como información. (RF-7, RF-11, RF-17)
- **C4 (M) — La comparación de valores en RF-4 no dice qué pasa con los vacíos.** Dos filas del mismo `id` y la misma campaña con `KVPI` vacío en las dos: en una comparación de decimales `NaN` no es igual a `NaN`, así que podrían leerse como "valores distintos" y dar un error. Y una con valor y otra vacía, ¿es un conflicto o se toma el valor? (RF-4)
- **C5 (M) — No se dice qué textos cuentan como "vacío".** La lectura de la spec 001 usa los vacíos de `pandas`: la celda vacía, pero también `NA`, `NaN`, `null` y `N/A`, que pasan a ser vacíos sin ningún aviso. Otros textos, como `-` o `n/d`, dan el error de RF-3. Es una regla implícita que conviene escribir. (RF-3)
- **C6 (M) — Qué hace `--min-campanas` con el promedio.** Con `min_campanas` mayor que 2, una planta que no llega conserva `KVPI_mean` pero no `KVPI_std`. Está en las dudas abiertas, pero decide qué valor sale en el CSV para esas plantas y qué ven `mapa` y `analizar` después. (RF-8, RF-10)
- **C7 (M) — Qué plantas faltan en el mapa y su efecto en la huella.** Las plantas del muestreo sin serie quedan fuera del CSV (RF-13), así que desaparecen del mapa de verificación. La huella (el conjunto de ids bajo malla) depende de qué plantas quedaron: una nueva exportación con distintas plantas sin dato da otra huella. No es un error, pero la spec no lo dice, y quien compare dos corridas puede no entender por qué cambia. (RF-13)
- **C8 (B) — Las columnas extra del muestreo pasan al resultado.** El muestreo de referencia trae `left`, `top`, `right`, `bottom` (coordenadas en metros de cada celda), `row_index` y `col_index`. RF-13 las conserva, y de ahí pasan a `plantas.csv` de `analizar`. Es coherente con la spec 003 (se conservan las columnas de entrada), pero agrega ruido a los resultados. (RF-13)
- **C9 (B) — `--min-campanas` con un valor que no es un número da código 2.** RF-10 pide un error de entrada (código 1) para un valor no permitido, pero un texto como `abc` lo rechaza antes la lectura de argumentos (código 2), igual que `--alfa` en la spec 003. Hay que decidir si es aceptable o si se unifica. (RF-10, RF-18)

## Criterios y diseño

- **C10 (M) — RESUELTO PARCIALMENTE (24/10/2026): con la serie real exportada, las diferencias máximas son 5,6e-17 (promedio) y 9,7e-17 (desvío); la spec fija la tolerancia en 1e-12. Falta decidir qué hacer si una exportación futura la supera.** ~~La tolerancia del criterio 3 queda sin fijar.~~ "Con una tolerancia que se fija al ver los datos" deja el criterio abierto justo donde decide si el cálculo está bien. El valor publicado tiene precisión completa (`0.4183376226741217`), así que lo razonable es fijar una regla antes: igualdad con una diferencia máxima, y qué hacer si se supera (informar la diferencia máxima y su causa, no ajustar la tolerancia para que pase). (Criterio 3)
- **C11 (B) — El criterio 4 mezcla dos cosas.** Pide que el flujo completo dé 16 "Mantener" y 19 "Intervenir" "con el estado de frío de la campaña 2024"; eso ya lo prueba la spec 003 sobre el CSV publicado. Lo nuevo que prueba el criterio 4 es que `kvpi` produce un CSV equivalente al publicado, es decir, que no cambia ningún valor de las 159 plantas. (Criterio 4)
- **C12 (B) — El archivo de la serie real tiene que entrar al repositorio con su procedencia.** Igual que el clima en la spec 002 (T2.0): de dónde salió la exportación, cuándo, con qué proyecto de Earth Engine, y qué versión de las imágenes. Sin eso, una diferencia con lo publicado no se puede explicar. (Criterio 3)

## Resumen
- **1 hallazgo grave (A):** C3 (campaña entera faltante sin aviso).
- **7 medios (M):** C1, C2, C4, C5, C6, C7 y C10.
- **4 menores (B):** C8, C9, C11 y C12.

El orden sugerido: **C3** (puede dar un promedio sobre menos campañas sin ninguna señal), **C1** (decide si el criterio 3 se puede cumplir con la serie real) y **C10** (decide cómo se mide el criterio 3).
