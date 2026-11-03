# Plan — Spec 005

Estado: BORRADOR. Sin código. Lee: `docs/constitution.md`, `spec.md` (RF-1 a RF-11) y `clarificacion.md`. Los hallazgos menores (C4 a C7) quedan como dudas abiertas; donde el plan necesita una decisión sobre uno de ellos, la toma la sección 8 y se puede cambiar.

## 1. Idea general

Un recuento nuevo que viaja junto al cálculo de frío que ya existe y llega hasta la pantalla y el resumen. **No hacen falta dependencias nuevas** (constitución #1): todo sale de `pandas`, y no cambia ningún cálculo.

```
clima.csv (con origen) ─► preparar_clima_con_origen ─► tabla (date, Tmax, Tmin, disponible, estimado)
                                  │                         │
                    preparar_clima (igual que hoy,          ▼
                    sin la columna estimado)        contar_estimados  ─► ResultadoClima.estimados   (RF-1 a RF-5)
                                                              │
                                  estado_frio_de_campana ◄────┘  copia el período elegido
                                         │                       ─► EstadoCampana.dias_estimados / proporcion_estimada
                                         ├─► advertencia DIAS_ESTIMADOS                               (RF-6, RF-7)
                                         ▼
                      elegir_estado_de_frio ─► EstadoDeFrio ─► resumen.json (estado_frio y parametros.clima)  (RF-11)
```

Sin la columna `origen` la columna `estimado` no se crea, `estimados` queda sin filas y todo lo demás da el mismo resultado de siempre (RF-2).

## 2. Módulos

| Módulo | Qué hace | RF que cubre |
|---|---|---|
| `kiwitracking/clima_parametros.py` (se amplía) | Campo `origenes_estimados` con su valor por defecto y su validación | RF-9 |
| `kiwitracking/clima_entrada.py` (se amplía) | `preparar_clima_con_origen`: lo mismo que `preparar_clima` más la columna `estimado`, con el `origen` de la primera aparición de cada fecha. `preparar_clima` pasa a llamarla y quitar esa columna | RF-1, RF-3, RF-4, RF-5 |
| `kiwitracking/clima_origen.py` (nuevo) | `contar_estimados(tabla, parametros)`: una fila por ventana con `dias_estimados` y `proporcion_estimada` | RF-1, RF-3, RF-5 |
| `kiwitracking/clima.py` (se amplía) | `ResultadoClima.estimados` (con valor por defecto vacío); `calcular_clima` lo llena | RF-1, RF-2 |
| `kiwitracking/campana.py` (se amplía) | `EstadoCampana.dias_estimados` y `.proporcion_estimada`; la advertencia `DIAS_ESTIMADOS` | RF-6, RF-7, RF-8 |
| `kiwitracking/flujo.py` (se amplía) | `EstadoDeFrio` con los dos campos; `parametros.clima` con `origenes_estimados` | RF-11 |
| `kiwitracking/salida.py` (se amplía) | Las dos claves nuevas de `estado_frio` en `resumen.json` | RF-11 |
| `kiwitracking/cli.py` (se amplía) | La opción `--origenes-estimados` y su validación | RF-10 |

`clima_origen.py` no lee archivos ni imprime (constitución #6, #9). `campana.py` sigue sin conocer la tabla diaria: solo lee `ResultadoClima`.

## 3. Modelo de datos

| Estructura | Campos |
|---|---|
| `ResultadoClima.estimados` | tabla con `periodo`, `dias_estimados` (entero) y `proporcion_estimada` (decimal, vacía si la ventana no tiene días disponibles); sin filas si el clima no trae `origen` |
| `EstadoCampana` (campos nuevos al final) | `dias_estimados: int \| None = None`, `proporcion_estimada: float \| None = None` |
| `EstadoDeFrio` (campos nuevos al final) | `dias_estimados`, `proporcion_estimada`, los dos con valor por defecto `None` |

Los campos nuevos van **después** de los existentes y con valor por defecto: hay tests que construyen estas estructuras de forma posicional.

## 4. Decisiones técnicas

| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D1 | `preparar_clima_con_origen` hace todo el trabajo y `preparar_clima` queda como una envoltura que quita la columna `estimado` | Agregar `estimado` al resultado de `preparar_clima` | Los tests de la spec 002 fijan que las columnas extra no pasan al resultado; así `preparar_clima` no cambia ni una columna |
| D2 | La columna `origen` se agrega a la tabla base antes de descartar fechas repetidas; la rutina de la spec 002 ya conserva la primera fila con todas sus columnas | Contar antes de descartar, o mirar todas las copias | RF-4 (C1): se usa el `origen` de la primera aparición, sin tocar la rutina |
| D3 | La etiqueta se normaliza a texto, sin espacios al inicio ni al final y con `casefold()`, y se compara con la lista normalizada igual; una celda vacía no es estimada | Comparar tal cual; quitar tildes | Spec: sin espacios y sin distinguir mayúsculas (C6) |
| D4 | `estimado` es verdadero solo si la etiqueta coincide **y** el día está `disponible`; el recuento agrupa por `etiqueta_ventana` sobre los días disponibles | Contar etiquetas aunque falten temperaturas | RF-3 y RF-1: la proporción es sobre los días que aportan al cálculo |
| D5 | `contar_estimados` devuelve una fila por cada ventana con al menos un día disponible, igual que la tabla `frio` | Una fila por cada ventana esperada | La búsqueda por período en `estado_frio_de_campana` es un cruce con `frio` |
| D6 | `estado_frio_de_campana` busca el período elegido en `resultado.estimados`; si no hay fila, deja los dos valores en `None` y no avisa | Lanzar un error | RF-2: un resultado armado a mano o sin `origen` sigue funcionando |
| D7 | La advertencia `DIAS_ESTIMADOS` se agrega al final de las del estado (después de `CAMPANA_NO_INDICADA` y `COBERTURA_PARCIAL`) con el formato de porcentaje de la spec 002 | Calcular el aviso en `flujo.py` | RF-6, RF-7: una sola definición, usable como biblioteca |
| D8 | `ParametrosClima.__post_init__` convierte la lista en tupla y valida que no esté vacía y que cada elemento sea un texto no vacío (después de quitar espacios) | Aceptar cualquier iterable | RF-9: el mismo estilo que `meses_frio` |
| D9 | `--origenes-estimados` recibe un texto y `interpretar_analizar` lo separa por comas y quita espacios; un valor vacío da `ErrorDeEntrada`. Se agrega a `OPCIONES_DE_CLIMA` | Una opción repetible | Coherente con `--campanas` de `kvpi`; el chequeo de "solo con `--clima`" ya existe (RF-10) |
| D10 | Solo se pasa `origenes_estimados` a `ParametrosClima` si se indicó; el valor por defecto sigue viviendo en `ParametrosClima` | Copiar `("interpolado",)` en la línea de comandos | Constitución #7 |
| D11 | `parametros.clima` de `resumen.json` toma `origenes_estimados` de `ParametrosClima` y lo escribe como lista, siempre | Escribirlo solo si se indicó | RF-11 (C3) |

## 5. Estrategia de pruebas

Mismas reglas: cada RF tiene un test que lleva su número (`test_rfN_...`), el test se escribe primero y se ve fallar, y al cerrar cada grupo se hacen mutaciones.

| Archivo de tests | Qué prueba | Datos |
|---|---|---|
| `test_clima_origen.py` | RF-1 a RF-5 y RF-9: recuento por ventana, sin `origen`, días sin temperaturas, fechas repetidas, orden de filas, validación de `origenes_estimados` | Climas sintéticos de pocas filas, con el valor de cada ventana contado a mano |
| `test_campana_estimados.py` | RF-6 a RF-8: el aviso, su orden, que no cambia estado ni horas, con y sin recuento | `ResultadoClima` armado a mano y desde `calcular_clima` |
| `test_flujo_estimados.py` | RF-11: `EstadoDeFrio`, `resumen.json` (`estado_frio` y `parametros.clima`) | Climas sintéticos en `tmp_path` |
| `test_cli_estimados.py` | RF-10: la opción, su separación por comas, errores, "solo con `--clima`" | `main(argv)` y `interpretar_analizar` |
| `test_clima_estimados_golden.py` | Criterios 3 a 5 con el clima real: 26 de 123 en 2024, 4 de 123 en 2023, 8 de 119 en 2025, el aviso, el resumen, 16/19 sin cambios, y el mismo clima sin la columna `origen` | `tests/golden/clima_diario.csv` |

Además se actualizan dos tests existentes de la spec 003: el que compara el diccionario completo de `parametros.clima` (gana la clave `origenes_estimados`) y el que fija las claves de `estado_frio` con origen `clima` (ganan `dias_estimados` y `proporcion_estimada`).

## 6. Riesgos

1. **El refactor de `preparar_clima`.** Lo usan todos los cálculos de clima. Se mitiga con D1 (misma salida que hoy) y con los tests actuales, que no deben cambiar ni una línea salvo el de `parametros.clima`.
2. **Estructuras construidas a mano en los tests.** Por eso los campos nuevos van al final y con valor por defecto (sección 3).
3. **Tipos de pandas con `origen`.** Una columna de texto con vacíos se lee como `NaN`; se normaliza con `astype("string")` antes de comparar, y se prueba con celdas vacías y etiquetas numéricas.
4. **Fechas repetidas.** El archivo real no tiene ninguna; el comportamiento se prueba solo con datos sintéticos.

## 7. Cobertura de requisitos

| RF | Módulo | Test |
|---|---|---|
| 1, 3, 5 | `clima_origen`, `clima_entrada` | `test_clima_origen`, `test_clima_estimados_golden` |
| 2 | `clima`, `clima_origen`, `campana` | `test_clima_origen`, `test_campana_estimados`, `test_clima_estimados_golden` |
| 4 | `clima_entrada` | `test_clima_origen` |
| 6, 7, 8 | `campana` | `test_campana_estimados`, `test_clima_estimados_golden` |
| 9 | `clima_parametros` | `test_clima_origen` |
| 10 | `cli` | `test_cli_estimados` |
| 11 | `flujo`, `salida` | `test_flujo_estimados`, `test_clima_estimados_golden` |

## 8. Decisiones provisionales sobre los hallazgos menores

Todas siguen como dudas abiertas y se pueden cambiar:

- **C4.** Si ninguna ventana es clasificable, el origen del estado es `ninguno`: no hay período que decida, ni aviso, ni recuento en `resumen.json`.
- **C5.** Una columna `origen` presente pero totalmente vacía da recuentos en 0 y ningún aviso, igual que un clima totalmente medido; una columna ausente da `null`.
- **C6.** Las etiquetas se comparan sin espacios y sin mayúsculas, no sin tildes. Los textos que `pandas` lee como vacíos (`NA`, `null`, `N/A`) no se pueden listar.
- **C7.** El mensaje de `DIAS_ESTIMADOS` dice que los días no son mediciones, como pide RF-6, aunque la lista sea una propia.
