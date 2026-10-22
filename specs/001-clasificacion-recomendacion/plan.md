# Plan — Spec 001

Estado: BORRADOR. Sin código. Lee: `docs/constitution.md`, `spec.md` (RF-1 a RF-26) y `clarificacion.md`.

## 1. Idea general

Un pipeline lineal sobre una tabla de plantas. El **núcleo** trabaja con tablas ya cargadas y no toca archivos. Lo que sí toca archivos, coordenadas o mapas vive en capas aparte.

```
 capa E/S (io.py)                        núcleo                               capa visual
 leer CSV (RF-3, RF-4) ──┐                                                    mapa (RF-15)
 cruce con polígono ─────┤──► analizar(tabla, ...) ──► Resultado ◄── huella ──┘
 (RF-17..19)             │      validar → FC/p → decidir → corregir →
                         │      estabilidad → umbrales → ambiente →
                         │      recomendación → ajuste frío
```

## 2. Módulos

| Módulo | Capa | Qué hace | RF que cubre |
|---|---|---|---|
| `kiwitracking/resultado.py` | núcleo | Tipos de salida (`Resultado`, `Resumen`, `Advertencia`) y la excepción `ErrorDeEntrada` | RF-26 |
| `kiwitracking/validacion.py` | núcleo | Valida columnas, tipos y parámetros; excluye plantas con `KVPI_mean` vacío | RF-1, RF-2, RF-5, RF-14 |
| `kiwitracking/correccion.py` | núcleo | Calcula FC, p-valor y tamaños; decide si corregir; aplica la corrección | RF-6 a RF-13 |
| `kiwitracking/huella.py` | núcleo | Huella del conjunto de plantas bajo malla | RF-16 |
| `kiwitracking/clasificacion.py` | núcleo | Estabilidad, umbrales, ambiente, recomendación, ajuste por frío | RF-20 a RF-25 |
| `kiwitracking/analisis.py` | núcleo | `analizar(...)`: orquesta todo y arma el `Resultado` | RF-26 (y une el resto) |
| `kiwitracking/io.py` | E/S | Lee CSV como UTF-8, detecta texto corrupto en categorías, calcula `bajo_malla` por punto en polígono | RF-3, RF-4, RF-17, RF-18, RF-19 |
| `kiwitracking/visualizacion.py` | visual | Mapa de verificación; devuelve la huella | RF-15 |

El núcleo no importa nada de `io.py` ni de `visualizacion.py`. La dependencia va solo en una dirección.

## 3. Modelo de datos

**Entrada.** Un `DataFrame` de pandas con `id`, `KVPI_mean`, `KVPI_std`, `bajo_malla`. Parámetros: `correccion` ("auto" por defecto), `huella_confirmada` (vacía por defecto), `estado_frio_ultima_campana` (opcional) y los umbrales con su valor por defecto (`alfa=0.05`, `min_plantas_grupo=2`, `p_ambiente=(33, 66)`, `p_estabilidad=75`).

**Salida: `Resultado`.**
- `tabla`: `DataFrame` con las columnas de entrada más `KVPI_corregido`, `estabilidad`, `ambiente` y `recomendacion`.
- `resumen`: FC, p-valor, `n_bajo_malla`, `n_fuera_malla`, `correccion_aplicada` (bool), p33, p66, p75 de estabilidad y la huella calculada.
- `advertencias`: lista de `Advertencia(codigo, mensaje)`. El **código** es un identificador estable (por ejemplo `FALTA_CONFIRMACION`, `HUELLA_NO_COINCIDE`, `CORRECCION_FORZADA`, `PLANTAS_EXCLUIDAS`, `STD_CERO`, `SIN_ESTADO_FRIO`); los tests comprueban el código, no el texto.

## 4. Decisiones técnicas

| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D1 | Los errores de entrada son excepciones (`ErrorDeEntrada`, subclase de `ValueError`) | Devolver un resultado con un indicador de error | Un error debe detener el flujo. Es lo que pide la spec y lo más simple de testear. |
| D2 | Las advertencias se acumulan en el `Resultado` | Módulo `warnings` de Python | La spec (RF-26) las quiere en la salida. `warnings` se pierde en un notebook. |
| D3 | Percentiles con `numpy.percentile` (interpolación lineal) | Percentiles "a mano" | Ya coincide con los valores del golden (p33 = 0,5361; p66 = 0,5642). |
| D4 | Prueba t con `scipy.stats.ttest_ind(equal_var=True)` | Implementarla a mano; usar Welch | Student es lo que dice la metodología. Escribirla a mano exigiría la distribución t. Welch queda como duda abierta. |
| D5 | Huella = SHA-256 de los `id` bajo malla, como texto, ordenados y unidos; se guardan los primeros 12 caracteres | Hash de toda la tabla; un identificador aleatorio | Con todo el hash, cualquier cambio en el KVPI invalidaría la confirmación. Solo importa el conjunto de plantas bajo malla. |
| D6 | Mapa como HTML con `folium`, separando **los datos del mapa** (lista de puntos con su color) de su dibujo | PNG con matplotlib | Es interactivo y ya está en `requirements.txt`. Separar los datos permite testear sin abrir un navegador. |
| D7 | Cruce punto-en-polígono con `shapely` y conversión de coordenadas con `pyproj` | Hacerlo a mano | Es el estándar y ya está en el stack del proyecto original. |
| D8 | Precedencia al decidir la corrección: primero la huella (RF-8, RF-9), después la estadística (RF-11, RF-12) | Evaluar todo y acumular todas las causas | Una sola causa por corrida es más legible. |
| D9 | Entorno virtual `.venv` dentro del sandbox, con `pyproject.toml` | Instalar en el Python global | Aísla el sandbox y evita ensuciar tu instalación. |

## 5. Cambios que necesitan tu aprobación

La **constitución #1** dice: "Python 3.10+, pandas, numpy y pytest". El plan necesita más dependencias:

- **Núcleo:** `scipy` (prueba t, D4).
- **Capa E/S y visual (fuera del núcleo):** `shapely`, `pyproj` (D7) y `folium` (D6).

Propuesta de nueva redacción del principio #1: *"Python 3.10+; núcleo con pandas, numpy y scipy; entrada/salida y visualización con shapely, pyproj y folium; tests con pytest. Earth Engine queda fuera del núcleo."* No la edité: la constitución es tuya.

## 6. Estrategia de pruebas

Cada RF tiene al menos un test, y su nombre empieza con el número (`test_rf7_...`).

| Archivo de tests | Qué prueba | Datos |
|---|---|---|
| `test_validacion.py` | RF-1, RF-2, RF-5, RF-14 | Tablas sintéticas de 3 a 5 filas |
| `test_correccion.py` | RF-6 a RF-13: una tabla por rama de decisión (auto, forzar, desactivar, grupo chico, media ≤ 0, p ≥ 0,05) | Sintéticos con FC calculable a mano |
| `test_huella.py` | RF-16: mismo resultado sin importar el orden, cambia si cambia el conjunto | Sintéticos |
| `test_clasificacion.py` | RF-20 a RF-25, incluidos `std = 0`, empates en un umbral y el ajuste por frío | Sintéticos |
| `test_io.py` | RF-3, RF-4, RF-17 a RF-19 (CSV mal codificado, coordenadas distintas, cruce que da 0 o todas) | Archivos temporales |
| `test_visualizacion.py` | RF-15: los datos del mapa y la huella devuelta | Sintéticos |
| `test_golden.py` | Criterios de finalización 2 a 5 | `tests/golden/` (159 plantas) |

Detalles del golden:
- Entrada: columnas `KVPI_mean`, `KVPI_std` y `bajo_malla` del CSV de referencia.
- Comparación: tolerancia 1e-6 en valores numéricos, exacta en categorías.
- FC: 1,2262 con tolerancia 1e-3.
- p-valor: solo se comprueba p < 0,001, porque no hay un valor publicado.
- Cruce con el polígono: 53 plantas bajo malla.

## 7. Riesgos

1. **Python 3.14 es muy nuevo.** Puede que `scipy`, `pyproj` o `shapely` no tengan instaladores listos para Windows. La primera tarea lo comprueba, y el plan B es usar Python 3.12.
2. **Estabilidad inflada** (duda abierta): el golden usa el `std` sin corregir y los tests lo reproducen. Si más adelante se corrige, cambian los valores esperados.
3. **El golden viene de un solo lote.** Los tests prueban reproducibilidad, no validez agronómica (constitución #10).

## 8. Decisiones provisionales sobre los hallazgos menores

Para poder planificar tomé estos criterios. Todos siguen como dudas abiertas y se pueden cambiar:

- **C8.** Las plantas excluidas por RF-2 **no aparecen** en la tabla de salida; se informa cuántas fueron en una advertencia.
- **C7.** `bajo_malla` con valores distintos de 0 y 1 se valida como error en `validacion.py`, aunque RF-1 no lo nombra explícitamente.
- **RF-8 con `correccion = "desactivar"`.** La spec dice "cualquiera sea el valor de `correccion`", así que **se emite igualmente** la advertencia de falta de confirmación. Puede ser ruido; queda como duda.
- **C12.** Las advertencias llevan código estable (ver sección 3).

## 9. Cobertura de requisitos

| RF | Módulo | Test |
|---|---|---|
| 1, 2, 5, 14 | `validacion` | `test_validacion` |
| 3, 4 | `io` | `test_io` |
| 6 a 13 | `correccion` | `test_correccion` |
| 15 | `visualizacion` | `test_visualizacion` |
| 16 | `huella` | `test_huella` |
| 17, 18, 19 | `io` | `test_io` |
| 20 a 25 | `clasificacion` | `test_clasificacion` |
| 26 | `resultado` y `analisis` | `test_golden`, `test_clasificacion` |
