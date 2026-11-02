# Clarificación — Spec 005

Revisión crítica de `spec.md`. Esta fase **detecta** problemas; no los resuelve. Cada punto espera una decisión.

Severidad: **A** = condiciona el diseño o puede dar resultados mal fechados o mal asignados; **M** = ambigüedad que cambia resultados o impide testear; **B** = detalle.

## Lo que se verificó antes de revisar

- **Las cifras de la spec salen del archivo real.** `clima_diario.csv` tiene 2.604 filas, ninguna fecha repetida, ninguna celda de `origen` vacía y solo dos etiquetas (`INTA_verificado` y `interpolado`). Los 58 días interpolados tienen las dos temperaturas. En la ventana de invierno hay 4 días interpolados en 2023 (de 123), 26 en 2024 (de 123) y 8 en 2025 (de 119 disponibles).
- **Hoy `origen` se pierde en la primera etapa.** `preparar_clima` arma la tabla con `date`, `Tmax` y `Tmin`, y la rutina de fechas repetidas solo compara esas tres columnas y conserva la primera fila (la regla de la spec 002, que un test fija con una columna extra distinta). El recuento tiene que engancharse antes de esa pérdida.
- **El recuento por ventana tiene que viajar dentro de `ResultadoClima`.** `estado_frio_de_campana` solo recibe ese resultado; no ve la tabla diaria.
- **`COLUMNAS_FRIO` es un nombre público que los tests usan para armar tablas a mano.** `test_campana.py` y `test_clima_integracion.py` crean la tabla `frio` con `columns=COLUMNAS_FRIO` a partir de registros sin las columnas nuevas, y `test_clima.py` enumera las columnas.
- **`resumen.json` ya registra los parámetros de clima usados** (`parametros.clima`: `ventana_frio`, `formato_fecha`, `cobertura_minima`, `max_hueco_dias`, `campana`), y un test compara ese diccionario completo.

## Contradicciones e inconsistencias

- **C1 (M) — RF-4 cambia una regla de la spec 002 sin decir cuál.** La spec 002 (RF-4) conserva la primera fila de una fecha repetida e ignora las demás columnas; la spec 005 pide, para `origen`, contar el día como estimado si alguna fila lo es. Es una regla distinta para una columna que antes era "extra", y exige conservar el `origen` de todas las copias antes de descartarlas. El archivo real no tiene fechas repetidas, así que solo se puede probar con datos armados a mano. Hay que decidir si vale la pena (criterio conservador) o si basta con la regla de siempre (gana la primera). (RF-4, Casos límite)
- **C2 (M) — No se dice dónde vive el recuento ni cuánto cuesta.** RF-1 habla de `dias_estimados` y `proporcion_estimada` "para cada ventana de frío", pero no dice en qué estructura. Agregarlos a la tabla `frio` cambia `COLUMNAS_FRIO`, y la afirmación de que solo se actualizan "los tests que enumeran las columnas" subestima el efecto: también se rompen los que arman la tabla a mano. Alternativas: columnas nuevas en `frio` con valores vacíos cuando falten (y actualizar esos tests), o una estructura aparte dentro de `ResultadoClima` que no toque `COLUMNAS_FRIO`. Cambia el diseño y el costo. (RF-1, Requisitos no funcionales)
- **C3 (M) — La spec no dice si el parámetro nuevo se registra en `parametros.clima`.** `resumen.json` guarda los parámetros de clima usados para poder reproducir la corrida. `origenes_estimados` cambia lo que se avisa, pero la spec solo agrega dos claves en `estado_frio`. Si se registra, cambia el diccionario que hoy compara un test; si no, dos corridas con listas distintas dejan el mismo `parametros`. (RF-9, RF-11)

## Vacíos

- **C4 (B) — Falta el caso "no hay estado de frío por clima".** La spec cubre el estado escrito a mano (sin clima, sin aviso), pero no el clima sin ninguna ventana clasificable: el origen del estado es `ninguno`, no hay período que decida y por lo tanto no hay aviso ni recuento en `resumen.json`. Conviene escribirlo en los casos límite. (RF-6, RF-11)
- **C5 (B) — Hay dos formas distintas de "no se sabe" y solo una se distingue.** Una columna `origen` ausente da `null`; una presente pero con todas las celdas vacías da `0` y ningún aviso, igual que un clima totalmente medido. Quien exporte el clima sin completar la columna creerá que no hay días estimados. (RF-1, RF-2)
- **C6 (B) — Cómo se comparan las etiquetas.** Se comparan sin espacios y sin distinguir mayúsculas, pero no sin tildes (a diferencia de `--estado-frio` en la spec 003), y los textos que `pandas` lee como vacíos (`NA`, `null`, `N/A`) llegan como celdas vacías y no se pueden listar en `--origenes-estimados`. Es un detalle, pero conviene escribirlo. (Entradas, RF-9)
- **C7 (B) — El mensaje afirma "no son mediciones" aunque la lista sea otra.** RF-6 pide aclarar que los días no son mediciones. Es cierto para `interpolado`; con una lista propia (por ejemplo `satelital`) el programa no sabe qué significa la etiqueta. Más seguro: nombrar la etiqueta o las etiquetas que coincidieron y decir que figuran como estimadas, sin interpretar. (RF-6)

## Resumen
- **0 hallazgos graves (A).**
- **3 medios (M):** C1, C2 y C3.
- **4 menores (B):** C4, C5, C6 y C7.

El orden sugerido: **C2** (decide el diseño y qué tests se tocan), **C1** (decide si se cambia una regla de la spec 002) y **C3** (decide qué queda registrado en el resumen).
