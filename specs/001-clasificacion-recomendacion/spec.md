# Spec 001 — Corrección por malla, clasificación de ambientes y recomendaciones

Estado: IMPLEMENTADA y VALIDADA (ver `validacion.md`)

## Contexto y objetivo
KiwiTrackingIA calcula hoy, en notebooks, el tramo final de su metodología: corrige el KVPI de las plantas bajo malla de protección, clasifica ambientes y emite una recomendación de manejo por planta. Este tramo no tiene tests y depende de Colab. Esta spec define ese comportamiento como un núcleo Python verificable que reproduce los resultados publicados (v1.1, lote "El Abrojito", 159 plantas).

## Usuarios / actores
- **Investigador/a** que ejecuta el análisis y valida visualmente la malla.
- **Técnico/a de campo** que lee ambientes y recomendaciones.

## Historias de usuario
- **H1.** Como investigador/a, quiero ver en un mapa qué plantas se marcaron bajo malla y confirmarlo antes de que se corrija el KVPI, para no aplicar una corrección sobre un polígono mal dibujado.
- **H2.** Como investigador/a, quiero conocer FC, p-valor y tamaño de cada grupo, para entender por qué se corrigió o no.
- **H3.** Como técnico/a, quiero un ambiente y una recomendación por planta, para decidir dónde actuar.
- **H4.** Como investigador/a, quiero que los datos defectuosos produzcan errores o advertencias claras, para no obtener resultados engañosos.

## Entradas
Tabla por planta con: `id`, `KVPI_mean`, `KVPI_std`, `bajo_malla` (0/1). Opcionales: coordenadas con su sistema de coordenadas y el polígono de malla (para calcular `bajo_malla` y para el mapa), `estado_frio_ultima_campana` ("Deficiente", "Adecuado", "Óptimo"), `correccion` ("auto" por defecto, "forzar" o "desactivar"), `huella_confirmada` (texto, por defecto vacío; la huella que devolvió el mapa de verificación, ver RF-15 y RF-16) `escalar_std` (bool, verdadero por defecto; ver RF-27) y `prueba_t` ("welch" por defecto o "student"; ver RF-6 y RF-28).

## Requisitos funcionales

**Validación de entrada**
- **RF-1.** SI falta alguna columna obligatoria (`id`, `KVPI_mean`, `KVPI_std`, `bajo_malla`), o la tabla está vacía, o `KVPI_mean` contiene valores no numéricos, ENTONCES el sistema DEBE detenerse con un error que nombre el problema.
- **RF-2.** SI hay plantas con `KVPI_mean` vacío, ENTONCES el sistema DEBE excluirlas del análisis, y DEBE registrar una advertencia con la cantidad excluida.
- **RF-3.** La capa de entrada y salida (separada del núcleo) DEBE leer los CSV como UTF-8. SI un archivo no decodifica como UTF-8, ENTONCES DEBE detenerse con un error que indique el problema de codificación.
- **RF-4.** SI una columna de categorías (`ambiente`, `recomendacion`, `estado_frio`, `estado_frio_ultima_campana`) de un CSV contiene secuencias típicas de texto corrupto (`Ã`, `Â`, `â€`), ENTONCES la capa de entrada y salida DEBE detenerse con un error que nombre la columna y el valor. La detección se limita a esas columnas.
- **RF-5.** SI `estado_frio_ultima_campana` tiene un valor distinto de "Deficiente", "Adecuado" u "Óptimo" (comparación exacta, sensible a mayúsculas y tildes), ENTONCES el núcleo DEBE detenerse con un error que nombre los valores permitidos.

**Corrección por malla**
- **RF-6.** El sistema DEBE calcular, a partir de los datos, FC = media(`KVPI_mean` fuera de malla) / media(`KVPI_mean` bajo malla), el p-valor de la prueba t entre ambos grupos y el tamaño de cada grupo, y DEBE incluirlos en la salida. Por defecto (`prueba_t` = "welch") la prueba no supone varianzas iguales; con `prueba_t` = "student" sí las supone (como en el análisis publicado, v1.1).
- **RF-7.** CUANDO `correccion` sea "auto" Y p < 0,05 Y cada grupo tenga al menos 2 plantas Y la media de `KVPI_mean` bajo malla sea mayor que 0 Y `huella_confirmada` coincida con la huella de la tabla (RF-16), el sistema DEBE calcular `KVPI_corregido = KVPI_mean × FC` solo para las plantas con `bajo_malla = 1`, y `KVPI_corregido = KVPI_mean` para las demás.
- **RF-8.** MIENTRAS `huella_confirmada` esté vacía, el sistema NO DEBE aplicar ninguna corrección, cualquiera sea el valor de `correccion` (`KVPI_corregido = KVPI_mean`), y DEBE registrar una advertencia indicando que falta la validación visual.
- **RF-9.** SI `huella_confirmada` no está vacía pero no coincide con la huella de la tabla (por ejemplo, cambió `bajo_malla` después de confirmar), ENTONCES el sistema NO DEBE aplicar ninguna corrección y DEBE registrar una advertencia indicando que la confirmación no corresponde a estos datos.
- **RF-10.** SI todas o ninguna de las plantas tienen `bajo_malla = 1`, ENTONCES el sistema DEBE tomar `KVPI_corregido = KVPI_mean` sin emitir error.
- **RF-11.** SI `correccion` es "auto" y p ≥ 0,05, o algún grupo tiene menos de 2 plantas, o la media bajo malla no es mayor que 0, ENTONCES el sistema DEBE tomar `KVPI_corregido = KVPI_mean` y DEBE registrar una advertencia con la causa.
- **RF-12.** CUANDO `correccion` sea "forzar" Y `huella_confirmada` coincida con la huella de la tabla Y cada grupo tenga al menos 2 plantas Y la media bajo malla sea mayor que 0, el sistema DEBE aplicar la corrección aunque p ≥ 0,05, y DEBE registrar una advertencia de "corrección forzada" que incluya el p-valor. SI no se cumplen las condiciones de grupos o de media, DEBE tomar `KVPI_corregido = KVPI_mean` y registrar la causa.
- **RF-13.** CUANDO `correccion` sea "desactivar", el sistema NO DEBE corregir (`KVPI_corregido = KVPI_mean`), cualquiera sea el p-valor.
- **RF-14.** SI `correccion` tiene un valor distinto de "auto", "forzar" o "desactivar", ENTONCES el sistema DEBE detenerse con un error que nombre los valores permitidos.
- **RF-15.** El sistema DEBE ofrecer una función de visualización, separada del núcleo, que genere un mapa de verificación con las plantas coloreadas según `bajo_malla` y el polígono de malla superpuesto, y que devuelva la huella de la tabla (RF-16).
- **RF-16.** El sistema DEBE calcular una huella de la tabla: un código determinista (SHA-256 abreviado) del conjunto de `id` con `bajo_malla = 1`, independiente del orden de las filas y de que un `id` aparezca repetido. Dos tablas con el mismo conjunto de plantas bajo malla DEBEN dar la misma huella, y cualquier cambio en ese conjunto DEBE cambiarla. La huella registra y ata la confirmación a los datos; no prueba que una persona haya mirado el mapa.
- **RF-17.** La capa de entrada y salida DEBE ofrecer una función que calcule `bajo_malla` por punto en polígono: recibe las plantas con coordenadas y el polígono de malla, y devuelve 1 para las plantas cuyo punto cae dentro del polígono y 0 para las demás.
- **RF-18.** Las plantas y el polígono DEBEN declarar su sistema de coordenadas. SI alguno no lo declara, ENTONCES el sistema DEBE detenerse con un error. SI los sistemas difieren, ENTONCES DEBE convertir uno al otro antes del cruce.
- **RF-19.** SI el polígono no está vacío y el cruce da 0 plantas o todas las plantas bajo malla, ENTONCES el sistema DEBE registrar una advertencia de posible error de coordenadas, y NO DEBE tratar el resultado como un lote sin malla de forma silenciosa.

**Estabilidad, ambientes y recomendaciones**
- **RF-20.** El sistema DEBE calcular `estabilidad = KVPI_corregido / KVPI_std` por planta. Por defecto (`escalar_std` verdadero) el `KVPI_std` se escala con el mismo FC que la media (RF-27); con `escalar_std` falso se usa sin corregir, como en el análisis publicado (v1.1).
- **RF-21.** SI `KVPI_std` es 0 para una planta, ENTONCES `estabilidad` DEBE quedar vacía, la recomendación DEBE ser "Observar" y DEBE registrarse una advertencia.
- **RF-22.** El sistema DEBE calcular p33 y p66 de `KVPI_corregido` y p75 de `estabilidad`, con interpolación lineal, sobre las plantas válidas del lote.
- **RF-23.** El sistema DEBE asignar el ambiente: "Alto Potencial" si `KVPI_corregido` ≥ p66; "Limitante" si < p33; "Transicional" en el resto.
- **RF-24.** El sistema DEBE asignar la recomendación: "Mantener" si `KVPI_corregido` ≥ p66 y `estabilidad` ≥ p75; "Intervenir" si `KVPI_corregido` < p33 y `estabilidad` ≥ p75; "Observar" en el resto. Por construcción, toda planta "Mantener" es "Alto Potencial" y toda planta "Intervenir" es "Limitante".
- **RF-25.** CUANDO `estado_frio_ultima_campana` sea "Deficiente", el sistema DEBE reclasificar "Mantener" a "Observar". SI no se informa, NO DEBE aplicar ajuste y DEBE registrar una advertencia.
- **RF-27.** CUANDO `escalar_std` sea verdadero (valor por defecto), el sistema DEBE dividir el `KVPI_corregido` por el `KVPI_std` multiplicado por el mismo FC con que se corrigió esa planta (1 para las plantas que no se corrigieron), de modo que `estabilidad` equivalga a `KVPI_mean / KVPI_std` en las plantas corregidas y no cambie para las demás. SI no se aplicó la corrección, `escalar_std` NO DEBE tener efecto.
- **RF-28.** SI `prueba_t` tiene un valor distinto de "welch" o "student", ENTONCES el sistema DEBE detenerse con un error que nombre los valores permitidos.
- **RF-29.** SI hay filas completamente idénticas (todas las columnas de la tabla, incluidos los vacíos), ENTONCES el sistema DEBE conservar una sola, descartar las repetidas y DEBE registrar una advertencia `ID_DUPLICADO` con la cantidad descartada. Vale para el análisis y para el mapa de verificación.
- **RF-30.** SI el mismo `id` aparece en filas que difieren en algún valor, ENTONCES el sistema DEBE detenerse con un error que nombre los `id` en conflicto (hasta 10). Vale para el análisis y para el mapa de verificación.
- **RF-31.** SI alguna planta tiene el `id` vacío, ENTONCES el sistema DEBE detenerse con un error que diga cuántas plantas no tienen `id`. Vale para el análisis y para el mapa de verificación.

**Salida**
- **RF-26.** El sistema DEBE devolver, junto a la tabla por planta, un resumen con FC, p-valor, tamaños de grupo, umbrales, si se aplicó la corrección, si se escaló el desvío (`escalar_std`), la prueba t usada y la lista de advertencias.

## Requisitos no funcionales
- El núcleo no lee ni escribe archivos ni contiene rutas fijas (constitución #6, #9).
- El núcleo no modifica la tabla de entrada.
- Umbrales (0,05; 2 plantas; percentiles) son parámetros con esos valores por defecto (constitución #7).
- Un lote de 10.000 plantas se procesa en menos de 5 segundos.

## Casos límite
- Lote sin malla (todas con `bajo_malla = 0`) → RF-10.
- `bajo_malla` con valores distintos de 0 y 1 → error (RF-1, valores no válidos).
- Plantas duplicadas por `id` → filas idénticas se descartan con advertencia (RF-29); filas distintas con el mismo `id` son un error (RF-30).
- Empates exactos en un umbral → rige el signo escrito en RF-23 y RF-24: en p66 la planta es "Alto Potencial" (y "Mantener" si es estable); en p33 es "Transicional" (y nunca "Intervenir").

## Fuera de alcance
- Descarga de Sentinel-2 y cálculo de KVPI (spec 003).
- GDD, horas de frío y anomalías (spec 002); acá solo se recibe el estado de frío.
- Mapa HTML interactivo final (Folium) y capas de topografía.
- Interfaz gráfica, línea de comandos, multiusuario.
- Cambiar la fórmula de `estabilidad`.
- Predecir rendimiento.

## Criterios de finalización
1. Todos los tests `RF-n` pasan.
2. Con `tests/golden/datos_plantas_completos.csv`: `KVPI_corregido`, `estabilidad` y umbrales coinciden con tolerancia 1e-6; `ambiente` y `recomendacion` coinciden exactamente (con la huella de las 159 plantas como `huella_confirmada`, estado de frío "Deficiente" y `escalar_std` falso, que reproduce v1.1).
3. FC calculado = 1,2262 con tolerancia 1e-3. (El 1,227 de la documentación sale de dividir las medias ya redondeadas, 0,541 / 0,441; el 1,226 es el FC exacto redondeado a 3 decimales.)
4. Con las coordenadas del golden y `tests/golden/malla_zona.geojson`, el cruce da 53 plantas bajo malla.
5. Sin ajuste de frío, el lote de referencia da 15 "Mantener" y 19 "Intervenir" con `escalar_std` falso (v1.1), y 16 y 19 con el valor por defecto (verdadero).
6. Cada RF tiene al menos un test asociado (fase de Validación).
7. Demostración manual: ejecutar el flujo sobre el lote y revisar el mapa de verificación.

## Dudas abiertas
- **[NECESITA ACLARACIÓN]** En modo "auto", si los dos grupos son válidos pero no se puede calcular el p-valor (ambos sin variación), la implementación no corrige y avisa (`P_NO_DISPONIBLE`). La spec no cubre este caso.
- **[NECESITA ACLARACIÓN]** Decisiones de implementación (T15): la huella se calcula sobre la tabla de entrada completa (antes de excluir plantas sin KVPI); si no queda ninguna planta con `KVPI_mean` válido se lanza `ErrorDeEntrada`.

## Historial de cambios
- **Cambio 1 (21/10/2026).** La estabilidad de las plantas bajo malla usaba el `KVPI_std` sin escalar con el FC, lo que la inflaba un 22,6 %. Se agrega el parámetro `escalar_std` (falso por defecto, para reproducir v1.1) y el requisito RF-27. RF-20 y RF-26 se ajustan.
- **Cambio 2 (21/10/2026).** La metodología usaba "< p33" para Limitante y "≤ p33" para Intervenir: una planta justo en p33 era "Transicional" e "Intervenir" a la vez. Se unifica con el borde estricto (RF-24) y se agrega el invariante Mantener ⊂ Alto Potencial e Intervenir ⊂ Limitante. Sin efecto en el lote de referencia (ninguna planta cae exactamente en p33).
- **Cambio 3 (21/10/2026).** La prueba t de Student supone varianzas iguales y en el lote de referencia no se cumple (la varianza bajo malla es el 23 % de la de fuera de malla; Levene p < 0,001). Se adopta la prueba de Welch por defecto y se mantiene Student con `prueba_t="student"` para reproducir v1.1. Se agrega RF-28; RF-6 y RF-26 se ajustan. En el lote de referencia no cambia ninguna decisión (p = 5,9e-35 con Welch frente a 1,0e-26 con Student), pero sí el p-valor del resumen. La metodología original (`docs/metodologia.md`, sección 5.1) dice "Student" y debe actualizarse.
- **Cambio 4 (21/10/2026).** (a) `id` duplicados: antes el sistema no avisaba y contaba dos veces la planta (con 10 filas repetidas del lote de referencia, el FC pasaba de 1,22617 a 1,22939 y cambiaban 2 recomendaciones). Ahora las filas idénticas se descartan con advertencia (RF-29) y los conflictos son un error (RF-30); la huella se calcula sobre el conjunto de `id`. (b) FC: no era un error del software; 1,227 es la división de medias redondeadas y 1,226 el FC exacto redondeado. Se cita como 1,2262 (valor calculado: 1,22617). Pendiente fuera de este sandbox: unificar README, `docs/metodologia.md` y `metadata_ejecucion.txt`.
- **Cambio 5 (21/10/2026).** La spec listaba `id` como entrada (sección Entradas) pero RF-1 no la exigía: una tabla sin `id` terminaba en un `KeyError` interno, una planta con `id` vacío pasaba sin aviso (y entraba a la huella como el texto "nan"), y dos plantas con `id` vacío daban un error confuso de "id repetidos: nan". RF-1 pasa a exigir `id` y el nuevo RF-31 rechaza los `id` vacíos, con mensajes claros.
- **Cambio 6 (22/10/2026).** `escalar_std` pasa a ser verdadero por defecto. Decisión: la corrección multiplica la media por el FC y, por consistencia matemática, el desvío debe escalar igual; dejarlo sin escalar inflaba un 22,6 % la estabilidad de las plantas bajo malla. Efecto en el lote de referencia: cambian 5 de 159 recomendaciones, el p75 de estabilidad baja de 15,185 a 14,932, y ambientes y `KVPI_corregido` no cambian. Los resultados publicados (v1.1) se reproducen con `escalar_std=False`. Se ajustan RF-20, RF-27 y los criterios 2 y 5.
