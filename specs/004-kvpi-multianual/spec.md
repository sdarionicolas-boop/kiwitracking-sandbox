# Spec 004 — KVPI multianual desde la serie por planta y campaña

Estado: BORRADOR (pendiente de clarificación)

## Contexto y objetivo
El flujo de las specs 001 a 003 arranca de un CSV de plantas que ya trae `KVPI_mean` y `KVPI_std`. Esos dos valores salen de un paso anterior que hoy vive en un notebook (`01_KVPI_Calculo.ipynb` del repo original): Google Earth Engine calcula, para cada planta y cada campaña, un valor de KVPI (el promedio de NDVI, NDRE, NDMI y EVI sobre Sentinel-2, con la mediana de las imágenes sin nubes de la campaña), y el notebook agrega esas campañas en indicadores por planta.

La referencia del cálculo publicado es el notebook 03 (`03_IVP_Kiwi_Producto_Final.ipynb`, celda 6: `groupby('id')['KVPI'].agg(['mean', 'std', 'count'])`); el notebook 01 hace lo mismo con `pivot_table` y agrega el CV.

Esta spec reescribe **solo la agregación multianual**: desde la serie larga por planta y campaña (la que exporta Earth Engine) hasta los indicadores por planta, y cierra el flujo con un comando que deja el CSV listo para `mapa` y `analizar`. Calcular los índices, la mediana por campaña y la descarga de imágenes quedan fuera: dependen de Earth Engine y no se pueden probar sin conexión.

La verificación contra lo publicado necesita la serie real. La persona responsable la volvió a exportar de Earth Engine el 24/10/2026 (`KVPI_serie_2019_2025 (1).csv`: 954 filas, 159 plantas por 6 campañas, sin vacíos ni repetidos) y se comprobó con `pandas` que promedio y desvío muestral (n−1) reproducen `KVPI_mean` y `KVPI_std` de las 159 plantas publicadas con una diferencia máxima de 5,6e-17 y 9,7e-17.

## Usuarios / actores
- **Investigador/a** que exporta la serie de Earth Engine y quiere pasar de ella a las recomendaciones del lote sin escribir código.
- **Técnico/a de campo** que recibe el CSV de plantas y lo usa con `mapa` y `analizar`.

## Historias de usuario
- **H1.** Como investigador/a, quiero que `KVPI_mean` y `KVPI_std` salgan de la serie exportada con una regla explícita y probada, para no depender de un notebook.
- **H2.** Como investigador/a, quiero saber cuántas campañas entraron en cada planta y qué plantas tienen pocas, para no confiar en un desvío armado con dos datos.
- **H3.** Como investigador/a, quiero un comando que una la serie con las coordenadas y deje el CSV listo para `mapa` y `analizar`.
- **H4.** Como investigador/a, quiero que una serie mal formada (filas repetidas con valores distintos, valores no numéricos, ids vacíos) dé un error claro y no un resultado engañoso.

## Entradas

**Serie** (CSV): una fila por planta y campaña. Columnas obligatorias: `id`, `campaña` (o `campana`) y `KVPI`. Las demás columnas de la exportación (`.geo`, `row`, `col`, `system:index`…) se ignoran. Una celda de `KVPI` vacía es una campaña sin dato.

**Muestreo** (CSV): una fila por planta. Columnas obligatorias: `id`, `X` e `Y`. Las demás (`row_index`, `col_index`…) se conservan.

**Comando:** `kiwitracking kvpi --serie serie.csv --muestreo muestreo.csv`, con (la opción se llama `--muestreo` y no `--plantas` porque en `mapa` y `analizar` `--plantas` es el CSV que ya trae `KVPI_mean` y `KVPI_std`, es decir, justamente la salida de este comando):
- `--salida`: archivo de resultados (por defecto, `plantas_kvpi.csv`).
- `--min-campanas`: mínimo de campañas para calcular el desvío (por defecto, 2; entero de 2 en adelante).
- `--campanas`: las etiquetas de campaña esperadas, separadas por comas (opcional; ver RF-22).
- `--cobertura-minima-campana`: proporción mínima de plantas con dato que debe tener cada campaña (por defecto, 0,5; entre 0 y 1).
- `--sobrescribir`: permite reemplazar el archivo de salida.
- `--depurar`: muestra la traza completa de un error inesperado.

**Núcleo:** `agregar_kvpi(serie, min_campanas=2, campanas=None, cobertura_minima_campana=0.5, total_plantas=None)` recibe la tabla de la serie ya cargada y devuelve la tabla por planta y las advertencias.

## Requisitos funcionales

**Validación de la serie**
- **RF-1.** SI falta alguna columna obligatoria (`id`, `KVPI` o `campaña`/`campana`), ENTONCES el sistema DEBE detenerse con un error que nombre las columnas que faltan. SI la serie está vacía, ENTONCES DEBE detenerse con un error. SI vienen a la vez `campaña` y `campana`, ENTONCES DEBE detenerse con un error que pida indicar una sola.
- **RF-2.** SI hay filas con `id` vacío o con `campaña` vacía, ENTONCES el sistema DEBE detenerse con un error que diga cuántas son.
- **RF-3.** SI `KVPI` contiene texto que no es un número, ENTONCES el sistema DEBE detenerse con un error que nombre la columna y muestre un ejemplo; si varios valores tienen coma decimal, DEBE mencionarlo como causa probable. SI hay valores infinitos, ENTONCES DEBE detenerse con un error que diga cuántos son. Un valor vacío NO es un error: es una campaña sin dato.
- **RF-4.** SI hay filas con el mismo `id` y la misma campaña y el mismo `KVPI`, ENTONCES el sistema DEBE conservar una sola y registrar una advertencia `KVPI_DUPLICADO` con la cantidad descartada. SI el mismo `id` y la misma campaña aparecen con valores distintos, ENTONCES DEBE detenerse con un error que nombre hasta 10 pares `id`/campaña en conflicto y cuántos más hay. Esta regla es deliberadamente más estricta que los dos notebooks (el 01 promedia los repetidos sin avisar y el 03 los cuenta como campañas separadas): un repetido con valores distintos indica una exportación defectuosa o un `id` en dos puntos, y ningún promedio lo corrige.
- **RF-5.** Las campañas DEBEN identificarse por su etiqueta de texto, sin espacios al inicio ni al final. El sistema NO DEBE interpretar, ordenar ni validar el formato de la etiqueta.
- **RF-6.** El resultado NO DEBE depender del orden de las filas de la serie ni de las columnas extra.

**Cálculo por planta**
- **RF-7.** El sistema DEBE calcular, por cada planta, `n_campanas` (la cantidad de campañas con dato) y `KVPI_mean` (el promedio de esas campañas). SI una planta no tiene ninguna campaña con dato, ENTONCES `KVPI_mean` DEBE quedar vacío y `n_campanas` en 0.
- **RF-8.** El sistema DEBE calcular `KVPI_std` como el desvío estándar muestral (divisor n−1) de las campañas con dato. SI `n_campanas` es menor que `min_campanas`, ENTONCES `KVPI_std` y `KVPI_cv` DEBEN quedar vacíos.
- **RF-9.** El sistema DEBE calcular `KVPI_cv = KVPI_std / KVPI_mean`. SI `KVPI_mean` es 0 o está vacío, ENTONCES `KVPI_cv` DEBE quedar vacío.
- **RF-10.** SI `min_campanas` no es un entero mayor o igual que 2, ENTONCES el sistema DEBE detenerse con un error que nombre los valores permitidos.

**Advertencias**
- **RF-11.** SI hay plantas con menos campañas con dato que campañas encontradas en la serie (las etiquetas distintas, tengan o no dato), ENTONCES el sistema DEBE registrar una advertencia `PLANTAS_CON_MENOS_CAMPANAS` con cuántas son y el rango de `n_campanas`.
- **RF-12.** SI hay plantas cuyo desvío quedó vacío por tener menos de `min_campanas`, ENTONCES el sistema DEBE registrar una advertencia `SIN_DESVIO` con cuántas son.

**Unión con el muestreo**
- **RF-13.** El sistema DEBE devolver solo las plantas presentes en la serie y en el muestreo, en el orden del muestreo, con las columnas `id`, `KVPI_mean`, `KVPI_std`, `KVPI_cv`, `n_campanas` y después las demás columnas del muestreo en su orden. Una planta de la serie sin coordenadas DEBE quedar fuera con una advertencia `PLANTAS_SIN_COORDENADAS` con la cantidad; una planta del muestreo sin serie DEBE quedar fuera con una advertencia `PLANTAS_SIN_SERIE` con la cantidad. SI ninguna planta está en los dos, ENTONCES el sistema DEBE detenerse con un error.
- **RF-14.** SI faltan columnas obligatorias del muestreo (`id`, `X` o `Y`), ENTONCES el sistema DEBE detenerse con un error que las nombre. SI hay `id` repetidos en el muestreo con todos los valores iguales, ENTONCES DEBE conservar una sola y avisar; SI el mismo `id` aparece con valores distintos, ENTONCES DEBE detenerse con un error que nombre hasta 10 `id` y cuántos más hay.

**Comando `kvpi`**
- **RF-15.** El comando DEBE leer la serie y el muestreo con la lectura de la spec 001 (UTF-8, tolera el BOM de Excel). SI un archivo no existe, ENTONCES DEBE terminar con un error que nombre el archivo.
- **RF-16.** El comando DEBE escribir el resultado en el archivo indicado, en UTF-8 sin BOM, con `\n` como salto de línea, números completos sin redondear y celdas vacías para los valores vacíos. SI el archivo ya existe y no se indicó `--sobrescribir`, ENTONCES DEBE terminar con un error sin tocarlo. SI falla la escritura, ENTONCES NO DEBE dejar un archivo a medio escribir.
- **RF-17.** El comando DEBE mostrar en pantalla la cantidad de plantas del resultado, las campañas encontradas con su cobertura (RF-20), cuántas plantas tienen cada cantidad de campañas, las advertencias y dónde quedó el archivo, con una línea que diga que ese archivo es el que se pasa como `--plantas` a `mapa` y `analizar`.
- **RF-18.** El comando DEBE terminar con código 0 cuando se completa, 1 con un error de entrada, 2 con un uso incorrecto y 3 con un error inesperado, con el mismo formato de mensajes que `mapa` y `analizar` (RF-19 de la spec 003).
- **RF-19.** El comando NO DEBE modificar los archivos de entrada, y ante un error NO DEBE dejar archivos de salida.

**Cobertura por campaña**
- **RF-20.** El sistema DEBE calcular, por cada campaña encontrada en la serie, cuántas plantas tienen dato y qué proporción son del total de plantas de referencia: las del muestreo en el comando, y las distintas de la serie en el núcleo (o `total_plantas`, si se indica). Una campaña sin ninguna planta con dato DEBE figurar con 0.
- **RF-21.** SI una campaña tiene una proporción de plantas con dato menor que `cobertura_minima_campana`, ENTONCES el sistema DEBE registrar una advertencia `CAMPANA_CON_POCOS_DATOS` que nombre la campaña, la cantidad de plantas con dato y su proporción. SI `cobertura_minima_campana` no es un número entre 0 y 1, ENTONCES DEBE detenerse con un error que lo diga.
- **RF-22.** CUANDO se indiquen las campañas esperadas, el sistema DEBE compararlas con las etiquetas encontradas en la serie (sin espacios al inicio ni al final). SI una esperada no aparece en la serie, o una encontrada no estaba entre las esperadas, ENTONCES DEBE detenerse con un error que las nombre. SI la lista está vacía o repite una etiqueta, ENTONCES DEBE detenerse con un error. SIN lista, una campaña que falta por completo en la serie no se puede detectar: el comando DEBE mostrar las campañas encontradas para que se revisen.

## Requisitos no funcionales
- El núcleo (`agregar_kvpi`) no lee ni escribe archivos ni contiene rutas fijas (constitución #6, #9); usa solo `pandas` y `numpy` (constitución #1).
- El núcleo no modifica la tabla de entrada.
- `min_campanas` y el valor por defecto de la salida son parámetros explícitos (constitución #7).
- La lectura y la escritura de archivos viven en la capa de entrada y salida, con UTF-8 (constitución #8).

## Casos límite
- Una sola campaña en toda la serie: todas las plantas tienen `n_campanas = 1`, `KVPI_std` y `KVPI_cv` quedan vacíos, y sale la advertencia `SIN_DESVIO` (no `PLANTAS_CON_MENOS_CAMPANAS`, porque ninguna planta tiene menos campañas que el máximo observado).
- Una planta con todas las campañas vacías: `KVPI_mean` vacío y `n_campanas = 0`; el análisis de la spec 001 la excluye con su aviso.
- Filas repetidas con valores distintos: error, no se promedian ni se cuentan dos veces (RF-4). La serie real exportada el 24/10/2026 no tiene ninguna.
- Etiquetas de campaña que difieren solo por espacios (`2019_2020` y `2019_2020 `): son la misma campaña (RF-5).
- Dos etiquetas distintas para la misma campaña real (por ejemplo `2019_2020` y `2019-2020`): se tratan como campañas distintas; no se corrige en silencio.
- Una campaña que falta por completo en la exportación (por ejemplo, un año con nubes en todo el lote): sin `--campanas` no se detecta y `KVPI_mean` se promedia sobre las campañas restantes; con `--campanas` da un error que la nombra (RF-22).
- Una campaña con una etiqueta escrita distinto en una parte de las filas (`2019_2020` y `2019-2020`): se ven como dos campañas, la segunda con poca cobertura, y dan `CAMPANA_CON_POCOS_DATOS` (RF-21); con `--campanas`, la desconocida da un error.
- Un valor de `KVPI` fuera de lo plausible (por ejemplo, 5): no se valida el rango; solo se exige que sea un número finito.
- El mismo `id` escrito como número en un archivo y con decimal (`4.0`) en el otro: se compara el valor leído y puede no coincidir (ver dudas abiertas).
- `KVPI_mean` negativo: se calcula `KVPI_cv` con el signo que resulte; solo 0 lo deja vacío.

## Fuera de alcance
- Descargar imágenes o conectarse a Google Earth Engine.
- Calcular NDVI, NDRE, NDMI, EVI o el KVPI por imagen, la mediana por campaña, la máscara de nubes y el muestreo a 10 m.
- La clasificación del notebook 01 (terciles) y la persistencia en años alto, medio y bajo.
- Los mapas y el análisis topográfico de los notebooks 01 y 02.
- La estabilidad (`KVPI_mean/KVPI_std`): la calcula la spec 001 sobre el valor corregido por malla.
- Otros cultivos (por ejemplo, el maíz de la carpeta de dron y satélite).

## Criterios de finalización
1. Todos los tests `RF-n` pasan, con avisos tratados como errores.
2. **Serie sintética:** con una serie armada a mano (varias plantas, campañas faltantes, una planta con una sola campaña), `KVPI_mean`, `KVPI_std` (n−1), `KVPI_cv` y `n_campanas` coinciden con los valores calculados a mano.
3. **Serie real:** con la serie exportada de Earth Engine para el lote de referencia (`tests/golden/`), `KVPI_mean` y `KVPI_std` de las 159 plantas coinciden con los de `datos_plantas_completos.csv` con una diferencia menor que 1e-12, y la serie real no trae filas repetidas ni vacíos (un test lo comprueba, para que una exportación futura que los traiga se vea enseguida).
4. **Flujo completo:** `kvpi`, `mapa` y `analizar` sobre esa serie dan 16 "Mantener" y 19 "Intervenir" con el estado de frío de la campaña 2024.
5. El comando `kvpi` da código 1 con un mensaje claro y sin traza ante cada error de entrada conocido, y no deja archivos a medio escribir.
6. Cada requisito tiene al menos un test asociado (fase de Validación).

## Dudas abiertas
- **[NECESITA ACLARACIÓN]** Se supone que en la exportación de Earth Engine un punto sin píxel válido en una campaña no genera una fila con `KVPI` vacío, sino que la fila no existe. Hay que confirmarlo con la serie real: de eso depende cuánto sirve la cobertura por campaña frente a las celdas vacías.
- *Resuelta el 24/10/2026:* el desvío publicado es el muestral (n−1) y una exportación nueva reproduce los valores publicados con una diferencia de ~1e-16.
- **[NECESITA ACLARACIÓN]** El `id` se compara tal como se lee. Un archivo con `4.0` y otro con `4` no coinciden; falta decidir si se normalizan los números enteros escritos con decimal.
- **[NECESITA ACLARACIÓN]** `KVPI_cv` con `KVPI_mean` negativo da un valor negativo, como el notebook. Alternativa: dejarlo vacío con cualquier media menor o igual que cero.
- **[NECESITA ACLARACIÓN]** No se valida el rango de `KVPI`; un valor absurdo entra al promedio sin aviso. Alternativa: un parámetro de rango plausible.
- **[NECESITA ACLARACIÓN]** Con `min_campanas` mayor que 2, las plantas que no llegan conservan `KVPI_mean` pero no `KVPI_std`; quizá debería quedar también vacío el promedio.
- **[NECESITA ACLARACIÓN]** En el notebook original, la imagen de cada campaña es la mediana de los KVPI de cada imagen, no el KVPI de las medianas de los índices; la metodología escrita es ambigua. No afecta esta agregación, pero conviene aclararlo en la documentación.
- **[NECESITA ACLARACIÓN]** Las ventanas de campaña del notebook van de junio a junio con fin el 30/06 y la siguiente empieza el 01/06: junio queda en dos campañas seguidas. Tampoco afecta esta agregación.
- **[NECESITA ACLARACIÓN]** EVI no está acotado a [−1, 1] como dice la metodología, y hay que verificar que la máscara de nubes `QA60` siga completada en las imágenes posteriores a 2022. Ambos puntos pertenecen al paso de Earth Engine.

## Historial de cambios
- **Clarificación (29/10/2026).** Se resolvió C2: en `kvpi` el archivo del muestreo se indica con `--muestreo`; `--plantas` queda solo para el CSV con `KVPI_mean` y `KVPI_std` de `mapa` y `analizar`, y la pantalla de `kvpi` lo recuerda (RF-17).
- **Clarificación (29/10/2026).** Se resolvió C1: la referencia es el notebook 03, y la regla de repetidos de RF-4 se mantiene, declarada como deliberadamente más estricta que los dos notebooks.
- **Serie real (24/10/2026).** La persona responsable exportó la serie de Earth Engine. Se comprobó que `KVPI_mean` y `KVPI_std` publicados se reproducen con promedio y desvío muestral (diferencias de ~1e-16), así que los criterios 3 y 4 dejan de estar pendientes y la tolerancia queda en 1e-12.
- **Clarificación (24/10/2026).** Se resolvió el hallazgo grave C3: la cobertura por campaña se calcula y se muestra siempre, una campaña con menos de la mitad de las plantas con dato avisa, y una lista opcional de campañas esperadas permite detectar una que falta (RF-11, RF-17, RF-20 a RF-22).
- **Borrador (24/10/2026).** Alcance acordado en la entrevista: solo la agregación multianual desde la serie exportada de Earth Engine, con comando `kvpi`, desvío muestral, mínimo de 2 campañas, salida `KVPI_mean`, `KVPI_std`, `KVPI_cv` y `n_campanas`, y verificación contra la serie real cuando se exporte.
