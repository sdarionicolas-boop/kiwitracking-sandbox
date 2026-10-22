# Tareas — Spec 001

Reglas: una tarea a la vez, en orden. En cada una, primero se escribe el test y se lo ve fallar; después el código mínimo para que pase. Cada tarea apunta a menos de 30 minutos. Al terminar: correr toda la suite, mostrar el resultado y marcar la casilla.

## Preparación

- [x] **T0. Entorno y esqueleto.** Crear `.venv`, `pyproject.toml` y el paquete `kiwitracking/` vacío; instalar pandas, numpy, scipy, shapely, pyproj, folium y pytest.
  - Cubre: ninguno (infraestructura).
  - Hecho cuando: `python -c "import pandas, numpy, scipy, shapely, pyproj, folium"` no da error dentro del `.venv`, y `python -m pytest` corre y no encuentra tests sin fallar. Si alguna librería no instala con Python 3.14, se documenta y se rehace el entorno con 3.12 antes de seguir.

- [x] **T1. Tipos de salida.** `resultado.py`: `Advertencia(codigo, mensaje)`, `Resumen`, `Resultado` y la excepción `ErrorDeEntrada`.
  - Cubre: RF-26 (estructura).
  - Hecho cuando: un test crea un `Resultado` con una advertencia, lee sus campos, y comprueba que `ErrorDeEntrada` es una subclase de `ValueError`.

## Validación de entrada

- [x] **T2. Columnas, tabla vacía y KVPI no numérico.**
  - Cubre: RF-1.
  - Hecho cuando: hay tests que fallan con `ErrorDeEntrada` y nombran el problema en tres casos: falta `KVPI_std`, la tabla está vacía y `KVPI_mean` contiene texto. Una tabla correcta no da error.

- [x] **T3. Valores de parámetros y de `bajo_malla`.**
  - Cubre: RF-5, RF-14 y la validación de `bajo_malla` ∈ {0, 1} (decisión provisional del plan).
  - Hecho cuando: un `correccion` inválido, un `estado_frio_ultima_campana` con otra mayúscula o tilde ("deficiente", "Optimo") y un `bajo_malla = 2` dan `ErrorDeEntrada` que nombra los valores permitidos; los valores válidos pasan.

- [x] **T4. Exclusión de plantas con KVPI vacío.**
  - Cubre: RF-2.
  - Hecho cuando: con 5 plantas, 2 con `KVPI_mean` vacío, la tabla devuelta tiene 3, la entrada original no cambió, y hay una advertencia `PLANTAS_EXCLUIDAS` con la cantidad 2.

## Huella

- [x] **T5. Huella de plantas bajo malla.**
  - Cubre: RF-16.
  - Hecho cuando: el mismo conjunto de `id` en otro orden da la misma huella; agregar o quitar una planta bajo malla la cambia; cambiar el KVPI sin tocar `bajo_malla` no la cambia; la huella es un texto de 12 caracteres.

## Corrección por malla

- [x] **T6. FC, p-valor y tamaños de grupo.**
  - Cubre: RF-6.
  - Hecho cuando: con una tabla de FC conocido a mano (por ejemplo, medias 0,6 y 0,5 → FC = 1,2), la función devuelve ese FC, el tamaño de cada grupo y un p-valor entre 0 y 1; con dos grupos casi idénticos el p-valor es alto.

- [x] **T7. Precedencia de la huella.**
  - Cubre: RF-8, RF-9.
  - Hecho cuando: con huella vacía no se corrige y sale `FALTA_CONFIRMACION`; con una huella que no coincide no se corrige y sale `HUELLA_NO_COINCIDE`; con la huella correcta se pasa a la decisión siguiente. Con `correccion="desactivar"` y huella vacía, sigue saliendo `FALTA_CONFIRMACION` (decisión provisional). *Nota: en T7 se verificó que la función no recibe `correccion`; la prueba integrada con "desactivar" se hace en T9.*

- [x] **T8. Decisión en modo "auto".**
  - Cubre: RF-7, RF-10, RF-11.
  - Hecho cuando: hay un test por rama: corrige con p < 0,05 y grupos válidos; no corrige con p ≥ 0,05, con un grupo de 1 planta y con media bajo malla ≤ 0, cada uno con su advertencia de causa; sin plantas bajo malla, o con todas bajo malla, no corrige y no da error.

- [x] **T9. Modos "forzar" y "desactivar" y aplicación de la corrección.**
  - Cubre: RF-12, RF-13.
  - Hecho cuando: con p ≥ 0,05, "forzar" corrige y emite `CORRECCION_FORZADA` con el p-valor; "forzar" con un grupo de 1 planta no corrige; "desactivar" nunca corrige; en los casos que corrigen, `KVPI_corregido` = `KVPI_mean` × FC solo para `bajo_malla = 1`.

## Clasificación

- [x] **T10. Estabilidad.**
  - Cubre: RF-20, RF-21.
  - Hecho cuando: `estabilidad` = `KVPI_corregido` / `KVPI_std`; con `KVPI_std = 0` queda vacía y sale `STD_CERO`.

- [x] **T11. Umbrales.**
  - Cubre: RF-22.
  - Hecho cuando: sobre una tabla de 11 valores conocidos, p33, p66 y p75 coinciden con `numpy.percentile` calculado a mano en el test; las plantas con `std = 0` no entran al p75 de estabilidad.

- [x] **T12. Ambiente.**
  - Cubre: RF-23.
  - Hecho cuando: una planta justo en p66 es "Alto Potencial"; justo en p33 es "Transicional"; por debajo, "Limitante".

- [x] **T13. Recomendación.**
  - Cubre: RF-24, RF-21 (planta con `std = 0` → "Observar").
  - Hecho cuando: hay un test por caso: "Mantener", "Intervenir", "Observar", un empate exacto en p33 con estabilidad alta (que da "Intervenir"), y una planta con estabilidad vacía que da "Observar".

- [x] **T14. Ajuste por horas de frío.**
  - Cubre: RF-25.
  - Hecho cuando: con "Deficiente", las "Mantener" pasan a "Observar"; con "Adecuado" u "Óptimo" quedan igual; sin el dato no hay ajuste y sale `SIN_ESTADO_FRIO`.

## Integración y golden

- [x] **T15. `analizar()` completa.**
  - Cubre: RF-26 y el encadenamiento de RF-1 a RF-25.
  - Hecho cuando: una tabla sintética de 12 plantas atraviesa todo el flujo y devuelve un `Resultado` con tabla, resumen (FC, p, tamaños, umbrales, huella, `correccion_aplicada`) y la lista de advertencias; la tabla de entrada no se modificó.

- [x] **T16. Test contra el golden.**
  - Cubre: criterios de finalización 2, 3 y 5.
  - Hecho cuando: con `tests/golden/datos_plantas_completos.csv`, la huella de las 159 plantas y estado de frío "Deficiente": `KVPI_corregido`, `estabilidad` y umbrales coinciden con 1e-6; `ambiente` y `recomendacion` coinciden exactamente; FC = 1,2262 ± 1e-3; p < 0,001. Sin ajuste de frío: 15 "Mantener" y 19 "Intervenir".

## Entrada y salida

- [x] **T17. Lectura de CSV en UTF-8.**
  - Cubre: RF-3.
  - Hecho cuando: un CSV UTF-8 se lee bien (con tildes); un CSV guardado en Windows-1252 con tildes da `ErrorDeEntrada` que menciona la codificación.

- [x] **T18. Texto corrupto en columnas de categorías.**
  - Cubre: RF-4.
  - Hecho cuando: un CSV UTF-8 válido con `Ã“ptimo` en `estado_frio` da un error que nombra la columna y el valor; el mismo texto en otra columna no da error.

- [x] **T19. Cruce punto-en-polígono con sistema de coordenadas.**
  - Cubre: RF-17, RF-18.
  - Hecho cuando: con un polígono cuadrado y 4 puntos conocidos (2 dentro, 2 fuera) sale `[1, 1, 0, 0]`; sin sistema de coordenadas declarado, error; con puntos en lon/lat y polígono en UTM, el resultado es el mismo que con ambos en el mismo sistema.

- [x] **T20. Advertencia por cruce sospechoso y golden del cruce.**
  - Cubre: RF-19, criterio de finalización 4.
  - Hecho cuando: si el cruce da 0 o todas las plantas con un polígono no vacío, sale la advertencia de posible error de coordenadas (y no se trata en silencio como lote sin malla); con las coordenadas del golden y `tests/golden/malla_zona.geojson`, el cruce da 53 plantas bajo malla.

## Visualización

- [x] **T21. Datos del mapa y huella devuelta.**
  - Cubre: RF-15 (parte 1), RF-16 (devolución).
  - Hecho cuando: una función devuelve la lista de puntos con su color según `bajo_malla` y la huella de la tabla, sin generar HTML todavía.

- [x] **T22. Mapa HTML de verificación.**
  - Cubre: RF-15 (parte 2).
  - Hecho cuando: se genera un archivo HTML con `folium` que contiene un marcador por planta y el polígono, y la función devuelve la misma huella que `huella()`.

## Cierre

- [x] **T23. Validación final y demostración.**
  - *Estado: matriz y demostración hechas (ver `validacion.md`). Revisión visual del mapa confirmada por la persona responsable (21/10/2026): los puntos bajo malla coinciden con la malla visible en la imagen.*
  - Cubre: criterios de finalización 1, 6 y 7.
  - Hecho cuando: la suite completa pasa; existe una tabla que nombra, para cada uno de los 26 RF, el test que lo cubre y su resultado; y se ejecuta el flujo real sobre el lote (cruce, mapa, huella, análisis) y se revisa el mapa a mano.

## Notas

- Al iniciar T0, `AGENTS.md` se actualiza con el comando de tests dentro del `.venv`.
- Las dudas abiertas (`id` duplicados, Student/Welch, `<` o `≤` en p33, estabilidad con `std` sin corregir) no tienen tarea: hoy se resuelven con el comportamiento provisional del plan.

## Cambio 1: `escalar_std` (RF-20, RF-26, RF-27)

Mismas reglas: una tarea a la vez, el test primero y visto fallar. Con el valor por defecto (`escalar_std` falso) nada de lo ya validado puede cambiar.

- [x] **T24. Estabilidad con `escalar_std`.**
  - Cubre: RF-20, RF-27, RF-21 (con `escalar_std`).
  - Hecho cuando: `calcular_estabilidad(tabla, escalar_std=True)` da `KVPI_mean / KVPI_std` (equivale a dividir `KVPI_corregido` por `KVPI_std` × FC de esa planta); en plantas no corregidas el resultado no cambia; el valor por defecto es falso y reproduce el comportamiento anterior; con `KVPI_std = 0` la estabilidad sigue vacía y avisa.

- [x] **T25. `analizar()` acepta `escalar_std` y lo informa.**
  - Cubre: RF-26, RF-27.
  - Hecho cuando: `analizar(..., escalar_std=True)` propaga el parámetro, el `Resumen` trae `escalar_std`, y si la corrección no se aplicó (por ejemplo, sin huella) la estabilidad es idéntica a la del modo por defecto.

- [x] **T26. Golden del cambio.**
  - Cubre: criterios 2 y 5 (por defecto) y la medición del cambio (con `escalar_std`).
  - Hecho cuando: con el valor por defecto todos los tests del golden siguen pasando sin tocarse; con `escalar_std=True` sobre las 159 plantas el p75 de estabilidad da 14,932, cambian exactamente 5 recomendaciones, y los ambientes quedan idénticos.

- [x] **T27. Validación del cambio.**
  - Cubre: criterio 6 de la spec (cada RF con test).
  - Hecho cuando: `validacion.md` pasa a 27 requisitos con su test, la suite completa pasa con `-W error` y el cambio queda commiteado.

## Cambio 2: borde estricto en p33 (RF-24)

Mismas reglas. Con tablas sin empates en p33 (como el lote de referencia) nada de lo ya validado puede cambiar.

- [x] **T28. Intervenir con borde estricto (`< p33`).**
  - Cubre: RF-24 y el invariante Mantener ⊂ Alto Potencial, Intervenir ⊂ Limitante.
  - Hecho cuando: una planta justo en p33 con estabilidad alta es "Observar" (y de ambiente "Transicional"); una apenas por debajo es "Intervenir"; el invariante se cumple con valores exactamente en los umbrales y en 40 tablas aleatorias con muchos empates; el test viejo que documentaba la asimetría fue reemplazado.

- [x] **T29. Golden y validación del Cambio 2.**
  - Cubre: criterios 2 y 5, y el invariante sobre el lote real.
  - Hecho cuando: los tests del golden siguen pasando sin tocarse (el lote no tiene empates en p33), el invariante se verifica sobre las 159 plantas con y sin `escalar_std`, `validacion.md` registra el cambio y queda commiteado.

## Cambio 3: `prueba_t` (RF-6, RF-26, RF-28)

Mismas reglas. Con `prueba_t="student"` el resultado publicado (v1.1) tiene que reproducirse exactamente.

- [x] **T30. `calcular_factor` con `prueba_t`.**
  - Cubre: RF-6, RF-28.
  - Hecho cuando: por defecto el p-valor es el de Welch; con `"student"` es el de varianzas iguales; el FC, los tamaños y la media no dependen de la prueba; un valor distinto de `"welch"` o `"student"` da `ErrorDeEntrada` que nombra los permitidos; el test viejo que fijaba Student por defecto fue reemplazado.

- [x] **T31. `analizar()` acepta `prueba_t` y lo informa.**
  - Cubre: RF-26, RF-28.
  - Hecho cuando: `analizar(..., prueba_t=...)` y `resolver_correccion` propagan el parámetro, el `Resumen` trae `prueba_t`, un valor inválido llega como error desde `analizar()`, y por defecto el resumen dice "welch".

- [x] **T32. Golden y validación del Cambio 3.**
  - Cubre: criterios 2, 3 y 5, y la reproducción de v1.1.
  - Hecho cuando: con `"student"` el p-valor del lote es 1,0e-26 (como en v1.1) y con Welch 5,9e-35; la decisión de corregir y todos los resultados del golden son idénticos con ambas; `validacion.md` registra el cambio (28 requisitos) y queda commiteado.

## Cambio 4: `id` duplicados (RF-16, RF-29, RF-30)

Mismas reglas. Un lote sin ids repetidos (como el de referencia) no puede cambiar en nada.

- [x] **T33. `descartar_duplicados`.**
  - Cubre: RF-29, RF-30.
  - Hecho cuando: las filas completamente idénticas se reducen a la primera, conservando el orden, con la advertencia `ID_DUPLICADO` y la cantidad descartada; el mismo `id` con algún valor distinto (KVPI, desvío, `bajo_malla` o una columna extra) da `ErrorDeEntrada` que nombra hasta 10 `id` y cuántos más hay; un conflicto manda sobre los duplicados exactos; la tabla de entrada no se modifica.

- [x] **T34. `analizar()`, el mapa y la huella.**
  - Cubre: RF-29, RF-30, RF-16.
  - Hecho cuando: `analizar()` y `preparar_mapa` descartan duplicados exactos y fallan ante conflictos; `ID_DUPLICADO` sale antes de `PLANTAS_EXCLUIDAS` en el orden de advertencias; la huella es la misma con y sin filas repetidas; con 10 filas duplicadas del lote de referencia el resultado es idéntico al del lote original (salvo la advertencia).

- [x] **T35. Golden y validación del Cambio 4.**
  - Cubre: criterios 2 a 5 (sin cambios) y la reproducción con duplicados.
  - Hecho cuando: los tests del golden pasan sin tocarse; el caso de las 10 filas repetidas da FC 1,22617 (no 1,22939); un test documenta de dónde salen 1,226 y 1,227; `validacion.md` registra el cambio (30 requisitos) y queda commiteado.

## Cambio 5: `id` obligatoria y sin vacíos (RF-1, RF-31)

Mismas reglas. El lote de referencia tiene todos sus `id`: nada de lo ya validado puede cambiar.

- [x] **T36. `id` obligatoria y sin vacíos.**
  - Cubre: RF-1, RF-31.
  - Hecho cuando: una tabla sin columna `id` da `ErrorDeEntrada` que la nombra (y no `KeyError`), también junto a otras columnas faltantes; una o varias plantas con `id` vacío (NaN, `None` o texto vacío) dan `ErrorDeEntrada` con la cantidad ("1 planta sin id", "2 plantas sin id"), tanto en `analizar()` como en `preparar_mapa`; dos `id` vacíos ya no se confunden con "id repetidos"; los `id` de texto completos pasan.

- [x] **T37. Validación del Cambio 5.**
  - Cubre: criterio 6 de la spec (cada RF con test).
  - Hecho cuando: `validacion.md` pasa a 31 requisitos (el pendiente de la columna `id` queda resuelto), el golden pasa sin tocarse, la suite completa pasa con `-W error` y el cambio queda commiteado.

