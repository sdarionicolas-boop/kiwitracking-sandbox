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

- [ ] **T23. Validación final y demostración.**
  - *Estado: matriz y demostración hechas (ver `validacion.md`). Pendiente: revisión visual del mapa por una persona.*
  - Cubre: criterios de finalización 1, 6 y 7.
  - Hecho cuando: la suite completa pasa; existe una tabla que nombra, para cada uno de los 26 RF, el test que lo cubre y su resultado; y se ejecuta el flujo real sobre el lote (cruce, mapa, huella, análisis) y se revisa el mapa a mano.

## Notas

- Al iniciar T0, `AGENTS.md` se actualiza con el comando de tests dentro del `.venv`.
- Las dudas abiertas (`id` duplicados, Student/Welch, `<` o `≤` en p33, estabilidad con `std` sin corregir) no tienen tarea: hoy se resuelven con el comportamiento provisional del plan.
