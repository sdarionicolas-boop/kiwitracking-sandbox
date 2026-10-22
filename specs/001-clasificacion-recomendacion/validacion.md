# Validación — Spec 001

Fecha de la corrida: 21/10/2026. Comando: `.venv\Scripts\python -m pytest -W error` → **252 tests, 252 pasan, 0 avisos**.

## 1. Matriz de requisitos

Un test "cubre" un RF cuando su nombre lleva el número (`test_rfN_...`). Los números salen de los nombres de los tests, no de una lectura semántica: la columna "Qué comprueba" resume lo esencial.

| RF | Tests | Resultado | Archivos | Qué comprueba |
|---|---|---|---|---|
| 1 | 11 | OK | test_validacion, test_analisis | Columnas obligatorias, tabla vacía, KVPI no numérico, `bajo_malla` ∈ {0,1} |
| 2 | 6 | OK | test_validacion, test_analisis | Exclusión de plantas sin KVPI con advertencia y sin tocar la entrada |
| 3 | 7 | OK | test_io | UTF-8 (con BOM de Excel), error de codificación con nombre de archivo |
| 4 | 13 | OK | test_io | Texto corrupto (`Ã`, `Â`, `â€`) solo en las 4 columnas de categorías |
| 5 | 10 | OK | test_validacion, test_clasificacion | Dominio de `estado_frio_ultima_campana` (exacto, con tildes) |
| 6 | 12 | OK | test_correccion | FC, p-valor de Student, tamaños de grupo, casos sin cálculo posible |
| 7 | 9 | OK | test_correccion, test_analisis | Corrección en modo "auto": solo bajo malla, p < alfa estricto |
| 8 | 9 | OK | test_correccion, test_analisis | Sin huella no se corrige en ningún modo |
| 9 | 7 | OK | test_correccion, test_analisis | Huella que no coincide bloquea, incluso "forzar"; se compara con la tabla completa |
| 10 | 3 | OK | test_correccion | Lote sin malla o todo bajo malla: sin corrección y sin error |
| 11 | 11 | OK | test_correccion, test_analisis | Causas de no corrección (p, grupo chico, media ≤ 0) con advertencia |
| 12 | 11 | OK | test_correccion, test_analisis | "forzar" con aviso `CORRECCION_FORZADA` y p-valor |
| 13 | 2 | OK | test_correccion | "desactivar" nunca corrige |
| 14 | 11 | OK | test_validacion, test_correccion, test_analisis | Modo inválido: error con los valores permitidos |
| 15 | 27 | OK | test_visualizacion | Datos del mapa, HTML con un marcador por planta, polígono, fondo opcional |
| 16 | 13 | OK | test_huella, test_visualizacion | Huella determinista, sin depender del orden, visible en el mapa |
| 17 | 14 | OK | test_io | Punto en polígono; lectura de GeoJSON |
| 18 | 8 | OK | test_io | Sistema de coordenadas obligatorio y conversión entre sistemas |
| 19 | 5 | OK | test_io | Advertencia si el cruce da 0 o todas las plantas |
| 20 | 6 | OK | test_clasificacion | `estabilidad` = `KVPI_corregido` / `KVPI_std` (std sin corregir) |
| 21 | 4 | OK | test_clasificacion, test_analisis | `std = 0`: estabilidad vacía, aviso y "Observar" |
| 22 | 6 | OK | test_clasificacion | p33, p66 y p75 con interpolación lineal |
| 23 | 5 | OK | test_clasificacion | Ambiente, con los bordes en p33 y p66 |
| 24 | 9 | OK | test_clasificacion | Recomendación, bordes y estabilidad vacía |
| 25 | 9 | OK | test_clasificacion, test_analisis | Ajuste por frío deficiente y aviso si falta el dato |
| 26 | 9 | OK | test_analisis, test_resultado | Resultado con tabla, resumen y advertencias en orden |

**Ningún RF queda sin test.** Los más delgados son RF-13 (2 tests) y RF-10 (3 tests); alcanzan para su comportamiento, pero son los primeros candidatos a reforzar.

## 2. Criterios de finalización

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Todos los tests RF pasan | **Cumplido** | 252/252 |
| 2 | `KVPI_corregido`, `estabilidad` y umbrales con tolerancia 1e-6; ambiente y recomendación exactos | **Cumplido** | `test_golden`: diferencia máxima 1,1e-16 y 2,3e-13; las 159 plantas coinciden |
| 3 | FC = 1,2262 ± 1e-3 | **Cumplido** | FC = 1,22617; p = 1,0e-26 |
| 4 | El cruce con `malla_zona.geojson` da 53 plantas | **Cumplido** | 53, y coincide planta por planta con el notebook |
| 5 | Sin ajuste de frío: 15 "Mantener" y 19 "Intervenir" | **Cumplido** | `test_golden` |
| 6 | Cada RF tiene al menos un test | **Cumplido** | Sección 1 |
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
- La huella se calcula sobre la tabla de entrada completa.
- Sin ninguna planta con KVPI válido: error.
- El borde del polígono cuenta como "dentro".

## 6. Dudas abiertas de método (te corresponden)

1. `estabilidad` usa el `KVPI_std` sin corregir: infla un 22,6 % la de las plantas bajo malla.
2. `<` frente a `≤` en p33 (Limitante frente a Intervenir).
3. Prueba t de Student frente a Welch.
4. `id` duplicados.
5. FC publicado como 1,226 / 1,227 y calculado 1,2262.

## Veredicto

**La spec 001 está cumplida.** Los 26 requisitos tienen test, los 252 pasan, el núcleo reproduce el resultado publicado de las 159 plantas y la verificación visual del mapa fue confirmada por una persona. Las limitaciones de la sección 4 y las dudas de las secciones 5 y 6 siguen vigentes.
