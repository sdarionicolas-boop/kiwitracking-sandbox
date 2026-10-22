# Clarificación — Spec 001

Revisión crítica de `spec.md`. Esta fase **detecta** problemas; no los resuelve. Cada punto espera una decisión.

**Nota de numeración:** los hallazgos C1 a C15 citan los RF con la numeración *anterior* a los cambios. Correspondencia con la numeración vigente de `spec.md`: 1→1, 2→2, 3→3, 3a→4, 3b→5, 4→6, 5→7, 6→8, 6a→9, 7→10, 8→11, 8a→12, 8b→13, 8c→14, 9→15, 9a→16, (nuevos 17 a 19), 10→20, 11→21, 12→22, 13→23, 14→24, 15→25, 16→26.

Severidad: **A** = contradice una decisión tomada o impide testear; **M** = ambigüedad que cambia resultados; **B** = detalle.

## Contradicciones

- **C1 (A) — RESUELTO: parámetro `correccion` con "auto"/"forzar"/"desactivar" (RF-5, RF-6, RF-8, RF-8a–c). También cubre media ≤ 0 (parte de C6). Falta renumerar los RF al cerrar los 4 graves.** ~~Falta el "forzar".~~ En la pregunta 1 se eligió la opción C: el usuario puede *forzar o desactivar* la corrección. La spec no tiene ningún RF para forzar. Hoy, con `confirmado=True` y p ≥ 0,05, RF-8 impide corregir sin que nadie pueda anularlo. (RF-5, RF-8)
- **C2 (A) — RESUELTO: dos capas. La capa de entrada/salida valida UTF-8 y texto corrupto solo en columnas de categorías (RF-3, RF-3a); el núcleo valida el dominio de `estado_frio_ultima_campana` (RF-3b, cubre también C9).** ~~RF-3 choca con la constitución.~~ RF-3 habla de CSV y de codificación, pero el núcleo no lee archivos (NFR, constitución #9). No queda claro en qué capa vive esa validación. Tampoco es testeable tal cual: no dice cómo se reconoce "codificación corrupta" (por ejemplo, la presencia de `Ã`).
- **C3 (M) — Limitante y Intervenir se superponen mal.** Limitante es `< p33` (RF-13) pero Intervenir es `≤ p33` (RF-14). Una planta exactamente en p33 sería "Transicional" e "Intervenir" a la vez. Ya figura como duda abierta, pero es una contradicción interna, no solo una duda.

## Vacíos

- **C4 (A) — RESUELTO: `confirmado` se reemplaza por `huella_confirmada`, un hash del conjunto de plantas bajo malla que devuelve el mapa (RF-6, RF-6a, RF-9, RF-9a). Límite declarado: ata la confirmación a los datos, no prueba que alguien miró.** ~~`confirmado` no garantiza nada.~~ Es un booleano que cualquiera puede pasar en `True` sin mirar el mapa. La spec lo llama "validación visual obligatoria" pero no dice si se acepta eso, ni si la confirmación queda atada a una versión concreta de `bajo_malla` (si el polígono cambia después de confirmar, la confirmación queda vieja).
- **C5 (A) — RESUELTO: el cruce punto-en-polígono entra al alcance, en la capa de entrada/salida, con sistema de coordenadas obligatorio y advertencia si da 0 o todas (RF-17, RF-18, RF-19 nuevos). Criterio: 53 plantas con el golden.** ~~Falta definir quién produce `bajo_malla`.~~ La metodología lo obtiene con un punto-en-polígono sobre `malla_zona.geojson`. La spec solo lo recibe como columna. No está dicho si calcularlo queda fuera de alcance, ni en qué sistema de coordenadas llegan los puntos (el golden usa lon/lat; el polígono y la grilla de campo están en UTM).
- **C6 (M) — RF-4 con casos numéricos extremos.** No cubre: media bajo malla ≤ 0 (el KVPI puede ser negativo, el FC pierde sentido), grupos sin variación (la prueba t da NaN) y p-valor NaN.
- **C7 (M) — Columnas que RF-1 y RF-2 no cubren.** `bajo_malla` vacío o con valores distintos de 0/1 aparece solo en "Casos límite", sin RF. `KVPI_std` vacío o negativo no está tratado. `id` duplicados está sin definir.
- **C8 (M) — "Plantas válidas" no está definido** (RF-12). ¿Entran en los percentiles las plantas con `KVPI_std = 0`? ¿Y las excluidas por RF-2 aparecen en la tabla de salida con campos vacíos, o desaparecen? Cambia los umbrales y el recuento.
- **C9 (M) — `estado_frio_ultima_campana` sin dominio.** RF-15 solo trata "Deficiente". No dice qué pasa con "deficiente" en minúscula, con "Óptimo" mal codificado, o con un valor desconocido.
- **C10 (M) — RF-9 (mapa) no es testeable.** No define el formato de salida (¿HTML?, ¿PNG?), las entradas (coordenadas, polígono, sistema de coordenadas), ni cómo se comprueba que "las plantas están coloreadas según `bajo_malla`". El fondo satelital necesita internet y un servicio de teselas; la spec no lo menciona.
- **C11 (M) — Sin plantas después de excluir.** RF-1 cubre tabla vacía al inicio, pero no el caso en que RF-2 deje cero plantas.
- **C12 (B) — RF-16 no define el formato.** "Resumen" y "lista de advertencias" no tienen estructura (¿diccionario?, ¿objeto?). Cada advertencia debería tener un código estable para poder testearse, no solo un texto.

## Criterios de finalización

- **C13 (M) — El golden no verifica RF-4.** No hay un p-valor publicado, así que el criterio 2 no comprueba la prueba t. Student frente a Welch queda sin evidencia.
- **C14 (B) — El criterio 4 sale de un cálculo mío** con `statistics.quantiles` (15 y 19), no de un archivo publicado. Solo los 19 "Intervenir" aparecen en el golden. Los 15 "Mantener" hay que tratarlos como esperados, no como referencia real.
- **C15 (B) — El requisito de 10.000 plantas en 5 s** no tiene justificación ni máquina de referencia. El lote real tiene 159.

## Observaciones metodológicas (no son defectos de la spec)

- La prueba t asume plantas independientes, pero las plantas vecinas están espacialmente correlacionadas. Puede subestimar el p-valor. No cambia lo que dice la spec; conviene que lo sepas.

## Resumen

3 contradicciones, 9 vacíos, 3 sobre criterios. Los de severidad A (C1, C2, C4, C5) bloquean el plan.
