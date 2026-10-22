# Validación — Spec 001

Fecha de la corrida: 21/10/2026 (incluye los Cambios 1 a 4, secciones 7 a 10). Comando: `.venv\Scripts\python -m pytest -W error` → **387 tests, 387 pasan, 0 avisos**.

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`). Los números salen de los nombres de los tests, no de una lectura semántica: la columna "Qué comprueba" resume lo esencial.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 11 | OK | test_analisis, test_validacion | Columnas obligatorias, tabla vacía, KVPI no numérico, `bajo_malla` ∈ {0,1} |
| 2 | 6 | OK | test_analisis, test_validacion | Exclusión de plantas sin KVPI con advertencia y sin tocar la entrada |
| 3 | 7 | OK | test_io | UTF-8 (con BOM de Excel), error de codificación con nombre de archivo |
| 4 | 13 | OK | test_io | Texto corrupto (`Ã`, `Â`, `â€`) solo en las 4 columnas de categorías |
| 5 | 10 | OK | test_clasificacion, test_validacion | Dominio de `estado_frio_ultima_campana` (exacto, con tildes) |
| 6 | 23 | OK | test_analisis, test_correccion | FC y p-valor de la prueba t (Welch por defecto, Student opcional), tamaños de grupo, casos sin cálculo posible |
| 7 | 9 | OK | test_analisis, test_correccion | Corrección en modo "auto": solo bajo malla, p < alfa estricto |
| 8 | 9 | OK | test_analisis, test_correccion | Sin huella no se corrige en ningún modo |
| 9 | 7 | OK | test_analisis, test_correccion | Huella que no coincide bloquea, incluso "forzar"; se compara con la tabla completa |
| 10 | 3 | OK | test_correccion | Lote sin malla o todo bajo malla: sin corrección y sin error |
| 11 | 11 | OK | test_analisis, test_correccion | Causas de no corrección (p, grupo chico, media ≤ 0) con advertencia |
| 12 | 11 | OK | test_analisis, test_correccion | "forzar" con aviso `CORRECCION_FORZADA` y p-valor |
| 13 | 2 | OK | test_correccion | "desactivar" nunca corrige |
| 14 | 11 | OK | test_analisis, test_correccion, test_validacion | Modo inválido: error con los valores permitidos |
| 15 | 27 | OK | test_visualizacion | Datos del mapa, HTML con un marcador por planta, polígono, fondo opcional |
| 16 | 17 | OK | test_analisis, test_huella, test_visualizacion | Huella determinista: no depende del orden de las filas, de los KVPI ni de ids repetidos; visible en el mapa |
| 17 | 14 | OK | test_io | Punto en polígono; lectura de GeoJSON |
| 18 | 8 | OK | test_io | Sistema de coordenadas obligatorio y conversión entre sistemas |
| 19 | 5 | OK | test_io | Advertencia si el cruce da 0 o todas las plantas |
| 20 | 6 | OK | test_clasificacion | `estabilidad` = `KVPI_corregido` / `KVPI_std` (std sin corregir por defecto, como en v1.1) |
| 21 | 5 | OK | test_analisis, test_clasificacion | `std = 0`: estabilidad vacía, aviso y "Observar" |
| 22 | 6 | OK | test_clasificacion | p33, p66 y p75 con interpolación lineal |
| 23 | 5 | OK | test_clasificacion | Ambiente, con los bordes en p33 y p66 |
| 24 | 52 | OK | test_clasificacion | Recomendación con bordes estrictos (Intervenir `< p33`), estabilidad vacía e invariante Mantener ⊂ Alto Potencial, Intervenir ⊂ Limitante |
| 25 | 9 | OK | test_analisis, test_clasificacion | Ajuste por frío deficiente y aviso si falta el dato |
| 26 | 12 | OK | test_analisis, test_resultado | Resultado con tabla, resumen (incluidos `escalar_std` y `prueba_t`) y advertencias en orden |
| 27 | 15 | OK | test_analisis, test_clasificacion | `escalar_std`: estabilidad = `KVPI_mean` / `KVPI_std` solo donde hubo corrección; sin efecto si no se corrigió |
| 28 | 10 | OK | test_analisis, test_correccion | `prueba_t` inválida: error con los valores permitidos (welch, student) |
| 29 | 15 | OK | test_analisis, test_validacion, test_visualizacion | Filas idénticas: se conserva una, aviso `ID_DUPLICADO` con la cantidad (análisis y mapa) |
| 30 | 7 | OK | test_analisis, test_validacion, test_visualizacion | Mismo `id` con valores distintos: error que nombra hasta 10 `id` y cuántos más |

**Ninguno de los 30 RF queda sin test.** Los más delgados son RF-13 (2 tests) y RF-10 (3 tests); alcanzan para su comportamiento, pero son los primeros candidatos a reforzar. Los 12 tests `test_cambio1_*`, los 7 `test_cambio2_*`, los 5 `test_cambio3_*` y los 2 `test_cambio4_*` de `test_golden` verifican los cambios contra el lote real y no llevan número de RF en el nombre. RF-24 pasa de 9 a 52 tests porque el invariante se prueba en 40 tablas aleatorias con empates.

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests RF pasan | **Cumplido** | 387/387 |
| 2 | `KVPI_corregido`, `estabilidad` y umbrales con tolerancia 1e-6; ambiente y recomendación exactos | **Cumplido** | `test_golden`: diferencia máxima 1,1e-16 y 2,3e-13; las 159 plantas coinciden |
| 3 | FC = 1,2262 ± 1e-3 | **Cumplido** | FC = 1,22617; p = 1,0e-26 |
| 4 | El cruce con `malla_zona.geojson` da 53 plantas | **Cumplido** | 53, y coincide planta por planta con el notebook |
| 5 | Sin ajuste de frío: 15 "Mantener" y 19 "Intervenir" | **Cumplido** | `test_golden` |
| 6 | Cada RF tiene al menos un test | **Cumplido** | Sección 1 (30 RF) |
| 7 | Demostración manual del flujo y revisión del mapa a mano | **Cumplido** | Flujo ejecutado de punta a punta sobre el lote real (sección 3). Revisión visual del mapa confirmada por la persona responsable el 21/10/2026: los puntos naranjas coinciden con la malla visible en la imagen. |

## 3. Demostración manual sobre el lote real

Flujo ejecutado con `tests/golden/`: lectura de CSV y GeoJSON → cruce → mapa → análisis.

- 159 plantas leídas; polígono en CRS84.
- Cruce: **53 plantas bajo malla**, sin avisos.
- Mapa generado en `resultados/mapa_verificacion.html`; huella **`c4e55ae105c6`**.
- Última campaña leída de `horas_frio_por_campana.csv`: 2025, 439 h, "Deficiente".
- Análisis con la huella confirmada: corrección aplicada (FC = 1,2262), sin advertencias.
- Distribución: Alto Potencial 54 (todas Observar), Transicional 52 (todas Observar), Limitante 53 (34 Observar, 19 Intervenir). Ninguna "Mantener", como en el notebook.

## 4. Lo que esta validación NO prueba

- **Validez agronómica.** Los tests prueban que el código hace lo que dice la spec y reproduce el notebook, no que el KVPI prediga rendimiento (constitución #10).
- **Un solo lote.** Todo el contraste real es con "El Abrojito".
- **La entrada es el KVPI ya calculado.** El cálculo del KVPI desde Sentinel-2 queda para la spec 003.
- **La visualización con fondo satelital** no se probó sin conexión por diseño; se prueba que el HTML lo pida, no que se vea.
- **La numeración de los tests** es por nombre. Un test con un número equivocado en su nombre pasaría desapercibido.

## 5. Decisiones de implementación fuera de la spec

Fueron tomadas para poder avanzar y siguen como dudas abiertas en `spec.md`:

- Plantas excluidas por KVPI vacío no aparecen en la salida.
- `bajo_malla` vacío es error; planta sin coordenadas es error.
- Con "forzar" y un grupo de 0 plantas se avisa `GRUPO_CHICO`.
- Sin p-valor calculable en modo "auto": no se corrige y se avisa (`P_NO_DISPONIBLE`).
- La advertencia `FALTA_CONFIRMACION` se emite aun con `correccion="desactivar"`.
- `Resumen.escalar_std` informa lo que efectivamente ocurrió: verdadero solo si se pidió y hubo corrección.
- La huella se calcula sobre la tabla de entrada completa.
- Sin ninguna planta con KVPI válido: error.
- El borde del polígono cuenta como "dentro".
- "Fila idéntica" (RF-29) es igual en todas las columnas de la tabla, no solo en las obligatorias; los vacíos cuentan como iguales entre sí.
- Una tabla sin columna `id` sigue dando `KeyError` en lugar de `ErrorDeEntrada` (RF-1 no la lista, aunque la sección Entradas sí). Pendiente de decidir.

## 6. Dudas abiertas de método (te corresponden)

1. ~~`estabilidad` con el `KVPI_std` sin corregir~~ **Resuelta con el Cambio 1** (sección 7): parámetro `escalar_std`. Queda decidir si pasa a ser el valor por defecto en una versión futura.
2. ~~`<` frente a `≤` en p33~~ **Resuelta con el Cambio 2** (sección 8).
3. ~~Prueba t de Student frente a Welch~~ **Resuelta con el Cambio 3** (sección 9): Welch por defecto, Student con `prueba_t="student"`.
4. ~~`id` duplicados~~ **Resuelta con el Cambio 4** (sección 10): filas idénticas se descartan con aviso; conflictos son error.
5. ~~FC publicado como 1,226 / 1,227 y calculado 1,2262~~ **Aclarada** (sección 10): son redondeos del mismo valor.

## 7. Cambio 1: `escalar_std` (RF-20, RF-26, RF-27)

Ciclo completo de SDD: duda detectada y medida → decisión (opción C: parámetro, falso por defecto) → spec primero → tareas T24 a T27 → tests vistos fallar → código mínimo → validación.

- **Por defecto nada cambia:** los 14 tests del golden y los 252 anteriores pasan sin tocarse, y el resultado de las 159 plantas sigue coincidiendo con el publicado.
- **Con `escalar_std=True`** (lote de referencia): estabilidad = `KVPI_mean` / `KVPI_std`; p75 de estabilidad de 15,185 a 14,932; cambian exactamente 5 recomendaciones (plantas 107 y 180, bajo malla, dejan "Intervenir"; 237 y 357 pasan a "Intervenir"; 215 pasa a "Mantener"); ambientes y `KVPI_corregido` idénticos; 16 "Mantener" y 19 "Intervenir" sin ajuste de frío.
- **Control no circular:** un test recalcula la regla con numpy desde los datos crudos y coincide con `analizar()`.
- **Sensibilidad:** dos mutaciones (ignorar `escalar_std`; aplicarlo siempre) hacen fallar 8 tests cada una.
- **Hallazgo:** aun con el cálculo consistente, las plantas bajo malla son menos estables (9,32) que las de afuera (14,46). La corrección ajusta el nivel del KVPI, no su variabilidad.

## 8. Cambio 2: borde estricto en p33 (RF-24)

- **Problema:** Limitante era `< p33` pero Intervenir era `≤ p33`: una planta justo en p33 era "Transicional" e "Intervenir" a la vez.
- **Decisión (opción A):** Intervenir pasa a `< p33`. Los ambientes no se tocan (RF-23). Invariante: toda "Mantener" es "Alto Potencial" y toda "Intervenir" es "Limitante".
- **Efecto en el lote de referencia: ninguno.** Ninguna de las 159 plantas cae exactamente en p33 ni en p66 (p33 interpolado cae entre dos valores distintos, 0,5359 y 0,5371). Los tests del golden pasaron sin modificarse.
- **Dónde sí importa:** en tablas con valores repetidos. De 40 tablas aleatorias con empates, 26 violaban el invariante antes del cambio y ninguna lo viola ahora.
- **Verificado en el lote real** para las 6 combinaciones de estado de frío y `escalar_std`.
- **Sensibilidad:** volver al `≤` hace fallar 29 tests, todos en `test_clasificacion`; el golden no los detecta, y es lo esperado, porque el lote no tiene empates. La protección está en los tests con tablas chicas y aleatorias.

## 9. Cambio 3: prueba t de Welch por defecto (RF-6, RF-26, RF-28)

- **Problema:** la prueba de Student supone varianzas iguales y en el lote de referencia no se cumple: la varianza bajo malla es el 23 % de la de fuera de malla (Levene p < 0,001).
- **Decisión (opción B):** `prueba_t="welch"` por defecto; `prueba_t="student"` reproduce v1.1. El resumen informa la prueba usada.
- **Efecto en el lote de referencia:** ninguna decisión ni resultado cambia (tabla, FC, umbrales y recomendaciones idénticos con ambas pruebas). Cambia solo el p-valor del resumen: 5,9e-35 con Welch frente a 1,0e-26 con Student; ambos son "p < 0,001".
- **Dónde sí importa:** en lotes con pocas plantas bajo malla. Ejemplo fijado en un test: 10 plantas fuera de malla casi sin variación y 3 bajo malla con mucha; Student da p = 0,0005 (corrige) y Welch p = 0,103 (no corrige).
- **Sensibilidad:** tres mutaciones (default a Student, "student" que usa Welch, "welch" que usa Student) hacen fallar un test cada una. La primera versión de los tests no las detectaba: `pytest.approx` tiene una tolerancia absoluta por defecto de 1e-12 que da por iguales dos p-valores minúsculos. Se corrigió con `abs=0`.
- **Aviso de scipy:** con un grupo de valores idénticos scipy emite "Precision loss…". Se verificó a mano que el p-valor es correcto y se silencia solo ese aviso.
- **Pendiente fuera de este sandbox:** `docs/metodologia.md` (sección 5.1) del repositorio original dice "prueba t de Student" y debe actualizarse.

## 10. Cambio 4: `id` duplicados y aclaración del FC (RF-16, RF-29, RF-30)

- **Problema (duplicados):** el sistema no avisaba y contaba dos veces la planta. Con 10 filas repetidas del lote de referencia, el FC pasaba de 1,22617 a 1,22939, las plantas bajo/fuera de malla de 53/106 a 58/111 y cambiaban 2 recomendaciones.
- **Decisión (opción B):** filas idénticas se descartan con `ID_DUPLICADO`; el mismo `id` con valores distintos es un error. Vale para el análisis y para el mapa; la huella pasó a ser la de un conjunto de `id`.
- **Efecto en el lote de referencia:** ninguno (sus `id` son únicos). Con las 10 filas repetidas, el resultado es idéntico al del lote original: misma tabla, mismo resumen, 53/106 y FC 1,22617, más la advertencia.
- **Sensibilidad:** tres mutaciones (no descartar duplicados, huella como lista, descartar conflictos en vez de dar error) hacen fallar 5, 5 y 7 tests.
- **FC 1,226 / 1,227:** no era un error del software. El FC exacto es 1,226172; 1,226 es ese valor redondeado a 3 decimales y 1,227 sale de dividir las medias ya redondeadas (0,541 / 0,441). Un test lo documenta. Se cita como 1,2262.
- **Pendiente fuera de este sandbox:** unificar el FC en el README, `docs/metodologia.md` y `metadata_ejecucion.txt`.

## Veredicto

**La spec 001 está cumplida, con los Cambios 1 a 4 incorporados.** Los 30 requisitos tienen test, los 387 pasan, el núcleo reproduce el resultado publicado de las 159 plantas y la verificación visual del mapa fue confirmada por una persona. Las limitaciones de la sección 4 y las dudas de las secciones 5 y 6 siguen vigentes.
