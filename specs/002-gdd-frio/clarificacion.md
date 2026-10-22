# Clarificación — Spec 002

Revisión crítica de `spec.md`. Esta fase **detecta** problemas; no los resuelve. Cada punto espera una decisión.

Severidad: **A** = condiciona el diseño o puede dar resultados mal fechados o mal asignados; **M** = ambigüedad que cambia resultados o impide testear; **B** = detalle.

## Contradicciones e inconsistencias

- **C1 (A) — RESUELTO: en modo "invierno", `meses_frio` debe ser continuo dentro de un año calendario; si no, error (RF-9). El soporte del cruce de año queda como mejora futura.** ~~La ventana de frío por año calendario reintroduce el artefacto si cruza el fin de año.~~ RF-13 agrupa "invierno" por año calendario y `meses_frio` es un parámetro libre. Con `meses_frio = (11, 12, 1, 2)` (un invierno del hemisferio norte), noviembre–diciembre de un año y enero–febrero del mismo año son dos inviernos distintos mezclados: el mismo error que se quiere corregir. La spec no dice si esa combinación se prohíbe, o si el período se define de otra forma (por ejemplo, etiquetado por el año de su primer mes). (RF-13, Entradas)
- **C2 (M) — RESUELTO junto con C16: el parámetro se llama `campana` (RF-22, RF-23).** ~~`invierno` ya no es un invierno en modo "temporada".~~ Con `ventana_frio="temporada"` la etiqueta de cada ventana es el año en que empieza la temporada, y esa ventana mezcla dos inviernos. El parámetro `invierno=2024` (RF-22, RF-23) tendría un significado distinto según el modo, y el error de RF-23 ("ese período no existe") no aclara cuál. (RF-22, RF-23)
- **C3 (M) — Las advertencias de cobertura son asimétricas.** Una ventana de frío completa con cobertura menor que 1 avisa `COBERTURA_PARCIAL` (RF-21), pero una temporada de GDD completa con cobertura menor que 1 no avisa nada (RF-18 solo cubre las incompletas). La temporada 2024 (361 de 365 días) quedaría con un GDD ligeramente subestimado y sin ninguna señal. (RF-18, RF-21)
- **C4 (M) — `PERIODO_INCOMPLETO` no distingue GDD de frío.** Ambas tablas usan el año como etiqueta, así que "2022" puede ser la temporada 2022 (GDD) o el invierno 2022 (frío). El código es el mismo y la spec no pide que el mensaje diga de cuál habla. (RF-18, RF-20)

## Vacíos

- **C5 (A) — RESUELTO: solo `AAAA-MM-DD` o `formato_fecha` explícito, sin inferir (RF-2).** ~~El formato de fecha no está definido.~~ RF-2 pide "leer como fecha", pero la lectura de pandas es silenciosa e inconsistente: con tu versión, `01/02/2019` se lee como 2 de enero (mes primero) y `03/04/2019` como 4 de marzo, mientras que `13/02/2019` da fecha vacía. Un CSV en formato local `dd/mm/aaaa` se fecharía mal sin error cuando los días son 12 o menos. Falta decidir qué formatos se aceptan (por ejemplo, solo `AAAA-MM-DD`, con o sin hora, o fechas ya convertidas). (RF-2)
- **C6 (M) — No se sabe qué columnas cuentan para decidir si una fecha repetida es un duplicado.** RF-4 dice "valores iguales", pero las demás columnas se ignoran (Entradas): una fila repetida con distinto `Precip` ¿es un duplicado descartable o un conflicto? En la spec 001 la comparación era sobre todas las columnas; acá no está dicho. (RF-4)
- **C7 (M) — RESUELTO junto con C5: una fecha vacía o ilegible es un error con la cantidad (RF-2).** ~~Una fecha vacía no está tratada.~~ Una celda vacía o `None` en `date` se convierte en fecha inválida (demostrado), pero RF-2 habla de valores "que no se pueden leer": no dice si una fecha ausente cuenta, ni si el día se ignora o es un error. (RF-2)
- **C8 (M) — Falta la precedencia en el modelo de coseno cuando `Tmax = Tmin = umbral`.** Se cumplen a la vez "24 si `Tmax ≤ umbral`" y "0 si `Tmin ≥ umbral`". El notebook evalúa primero la de 24 h, pero la spec no lo establece. (RF-11)
- **C9 (M) — Las tablas de salida no tienen columnas definidas.** Los criterios 2 y 3 comparan con `gdd_por_campana.csv` y `horas_frio_por_campana.csv` (columnas `temporada`, `GDD_total`, `Horas_Frio`, `estado_frio`), pero RF-26 no fija nombres, tipos ni orden, ni cómo se llama la etiqueta del período en modo "invierno". (RF-26)
- **C10 (M) — Los días sin fila y los días con valor vacío están definidos por separado.** RF-7 trata los valores vacíos como faltantes; las fechas ausentes (sin ninguna fila) solo están implícitas en RF-14. Conviene decir explícitamente que ambos casos cuentan igual. (RF-7, RF-14)
- **C11 (M) — La comparación con `cobertura_minima` es sensible al punto flotante.** Multiplicar puede rechazar un período que cumple justo el mínimo: `0.28 × 25 = 7.000000000000001`, de modo que "7 de 25 días con mínimo 0,28" daría incompleto, mientras que dividir (`7 / 25 ≥ 0.28`) acierta. (Corrección del 22/10/2026: el ejemplo original, 57 de 100 con 0,57, no discriminaba; con él ambas formas dan completo.) La spec no dice cómo se compara. (RF-15)
- **C12 (M) — Los textos del estado deben ser exactamente los de la spec 001.** RF-22 dice "utilizable como `estado_frio_ultima_campana`", pero la spec 001 rechaza cualquier valor que no sea exactamente "Deficiente", "Adecuado" u "Óptimo" (con tilde y mayúscula). Falta pedir que ambas specs compartan una sola definición. (RF-20, RF-22)
- **C13 (M) — No está dicho si el sistema lee archivos.** El requisito no funcional dice "si se ofrece" una lectura. Los criterios necesitan leer CSV. Además, una columna con coma decimal (`27,4`) se lee como texto (demostrado) y daría el error de RF-3, sin sugerir la causa. (NFR, RF-3)
- **C14 (B) — Falta el orden entre advertencias de GDD y de frío.** RF-26 ordena por período, pero no dice cuál va primero cuando una temporada de GDD y un invierno comparten año. (RF-26)
- **C15 (B) — RESUELTO PARCIALMENTE (T2.0): 2.546 de los 2.604 días son idénticos a INTA (Miramar, dos descargas) y 58 no se pueden verificar; el archivo se copió completo con una columna `origen` y la advertencia quedó en `AGENTS.md`. Siguen sin verificarse el origen de esos 58 días y las condiciones de uso de los datos de INTA.** ~~Se desconoce la procedencia y las condiciones del dato de clima.~~ El archivo de referencia está en la carpeta de otro proyecto, trae columnas de origen incierto (`Tmedia`, `horas_frio`, `unidades_frio`) y tiene 40 fechas faltantes. Antes de copiarlo a `tests/golden/` y subirlo al repositorio remoto conviene saber de dónde viene y bajo qué condiciones se puede usar. (Criterios)

## Criterios y diseño

- **C16 (A) — RESUELTO: parámetro `campana` que enlaza la campaña Y con el período Y; sin indicarlo se usa el más reciente clasificable y se avisa `CAMPANA_NO_INDICADA` (RF-23, RF-28).** ~~El invierno elegido puede ser posterior a las campañas analizadas.~~ RF-22 toma el invierno clasificable más reciente: con tus datos, el de 2025 (mayo–agosto de 2025). Pero la serie de KVPI llega a junio de 2025, así que ese invierno ocurre **después** de la última campaña observada; el que la precede es el de 2024 (1.129 h, "Óptimo"). Con tus datos el resultado numérico no cambia (con "Adecuado" u "Óptimo" no se ajusta nada, y siguen 16 "Mantener"), pero la regla conceptual sí: "la última campaña" del clima y la de KVPI no son la misma. Falta decidir cómo se relacionan. (RF-22, criterio 7, duda 8 de la spec)

## Observaciones metodológicas (no son defectos de la spec)

- **O1. El estado de frío depende del método de estimación.** La columna `horas_frio` que ya trae el archivo de clima (de origen incierto) y el modelo de coseno de la spec dan resultados distintos para el mismo invierno:

  | Invierno | Columna del archivo | Modelo de coseno |
  |---|---|---|
  | 2019 | 885 h (Adecuado) | 957 h (Óptimo) |
  | 2021 | 955 h (Óptimo) | 925 h (Adecuado) |
  | 2024 | 861 h (Adecuado) | 1.129 h (Óptimo) |

  En 3 de los 7 inviernos el estado cambia, y en 2024 la diferencia es de un 24 %. El modelo de coseno no está validado contra horas medidas; la spec lo toma del método original. Es una limitación del cálculo, no de la redacción.
- **O2. La cobertura en días no mide el sesgo del GDD.** Ya anotado en la spec: los huecos de verano pesan más que los de otoño. La regla del hueco máximo lo atenúa pero no lo elimina.

## Resumen

3 hallazgos graves (C1, C5, C16), 11 medios y 2 menores, más 2 observaciones. Los graves condicionan el plan.
