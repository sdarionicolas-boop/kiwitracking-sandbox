# Plan — Spec 004

Estado: BORRADOR. Sin código. Lee: `docs/constitution.md`, `spec.md` (RF-1 a RF-22) y `clarificacion.md`. Los hallazgos menores (C8, C9, C11 y C12) quedan como dudas abiertas; donde el plan necesita una decisión sobre uno de ellos, la toma la sección 8 y se puede cambiar.

## 1. Idea general

Un núcleo chico que agrega la serie por planta, y un comando que lo conecta con archivos. **No hacen falta dependencias nuevas** (constitución #1): todo sale de `pandas` y `numpy`, más lo que ya tienen `io.py`, `salida.py` y `cli.py`.

```
kvpi:  --serie ───────► leer_csv ─► agregar_kvpi ──────────────┐   (núcleo: RF-1 a RF-12, RF-20 a RF-22)
                                       │ por planta + cobertura │
       --muestreo ────► leer_csv ─► validar_muestreo ───────────┤   (RF-14)
                                                                ▼
                                                  unir_con_muestreo            (RF-13)
                                                                │
                                          plantas_kvpi.csv ◄────┘   (RF-16, escritura con limpieza)
                                          pantalla: plantas, campañas con cobertura,
                                                    cantidad por n_campanas, advertencias (RF-17)
```

El orden respeta el de las specs anteriores: primero se validan los argumentos, después se leen los archivos, después se calcula, y al final se escribe (RF-19).

## 2. Módulos

| Módulo | Qué hace | RF que cubre |
|---|---|---|
| `kiwitracking/kvpi.py` (nuevo) | `agregar_kvpi(serie, ...)`: valida la serie, quita repetidos, calcula por planta y por campaña, y arma las advertencias. `unir_con_muestreo(...)`: valida el muestreo y une | RF-1 a RF-14, RF-20 a RF-22 |
| `kiwitracking/flujo.py` (se amplía) | `ejecutar_kvpi(solicitud)`: lee los dos archivos, llama al núcleo y a la unión, y devuelve el resultado sin imprimir | RF-15, RF-19 |
| `kiwitracking/salida.py` (se amplía) | `escribir_plantas_kvpi(...)`: escribe el CSV con las reglas de formato y el chequeo de archivo existente | RF-16, RF-19 |
| `kiwitracking/cli.py` (se amplía) | Subcomando `kvpi`, sus opciones, la pantalla y los códigos de salida | RF-17, RF-18 |

`kvpi.py` no lee ni escribe archivos, no imprime y no conoce rutas (constitución #6, #9). `flujo.py` no importa `argparse`.

## 3. Modelo de datos

| Estructura | Campos |
|---|---|
| `CoberturaCampana` | `campana`, `plantas_con_dato`, `proporcion` |
| `ResultadoKvpi` | `tabla` (una fila por planta), `cobertura` (lista de `CoberturaCampana`, en orden de etiqueta), `advertencias` |
| `SolicitudKvpi` | `serie`, `muestreo`, `salida`, `min_campanas`, `campanas`, `cobertura_minima_campana`, `sobrescribir` |

Son `dataclass` sin lógica, como en la spec 003. Las advertencias usan `Advertencia` de `resultado.py`.

## 4. Decisiones técnicas

| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D1 | El cálculo es `groupby("id")["KVPI"].agg(["mean", "std", "count"])` de `pandas` (desvío con n−1) | Fórmulas propias con `numpy` | Es literalmente lo que produjo lo publicado (notebook 03); la diferencia de ~1e-16 ya se midió y no hay nada que reinventar |
| D2 | Las etiquetas de campaña y los `id` se pasan a texto y se les quitan los espacios antes de agrupar | Interpretar los años o convertir los `id` a número | RF-5: la etiqueta es texto opaco. Los `id` se leen como los lee `leer_csv` (la duda `4.0` frente a `4` sigue abierta) |
| D3 | Los repetidos se detectan con `drop_duplicates` sobre `(id, campaña, KVPI)`, que trata los vacíos como iguales; lo que sigue repetido en `(id, campaña)` es un conflicto | Comparar con `==` | RF-4 y C4: dos vacíos son iguales y vacío contra número es conflicto, sin casos especiales |
| D4 | La tabla del núcleo sale ordenada por `id` y la unión la reordena según el muestreo | Dejar el orden de entrada | RF-6: el resultado no depende del orden de las filas |
| D5 | La cobertura se calcula con las plantas que tienen dato por campaña (`KVPI` no vacío), dividida por `total_plantas` si se indica o por los `id` distintos de la serie | Contar filas de la serie | RF-20: una fila con `KVPI` vacío no es una planta con dato |
| D6 | El comando pasa `total_plantas = cantidad de plantas del muestreo` al núcleo | Usar los `id` de la serie | RF-20: la cobertura se mide contra el lote que se quiere analizar |
| D7 | Validar `min_campanas` y `cobertura_minima_campana` en `kvpi.py` y, en `cli.py`, convertir con `type=int` y `type=float`; un valor que no es número lo rechaza `argparse` (código 2) | Un tipo propio que dé código 1 | C9 (menor): mismo criterio que `--alfa` en la spec 003 |
| D8 | `PLANTAS_SIN_SERIE` y `PLANTAS_SIN_COORDENADAS` llevan la cantidad y los primeros 10 `id`, y el de `PLANTAS_SIN_SERIE` agrega la frase de la huella (C7) | Solo la cantidad | RF-13 |
| D9 | El CSV se escribe con el mismo código que `salida.py` usa para `plantas.csv` (UTF-8 sin BOM, `\n`, números completos, vacíos en blanco) y con limpieza si falla | Un escritor nuevo | Una sola definición de formato (RF-16) |
| D10 | `kvpi` ofrece las mismas banderas `--sobrescribir` y `--depurar` que los otros comandos, reusando `_opciones_comunes` | Opciones propias | Coherencia con las specs 003 (RF-18) |

## 5. Estrategia de pruebas

Las mismas reglas: cada RF tiene un test que lleva su número (`test_rfN_...`), el test se escribe primero y se ve fallar, y al cerrar cada grupo se hacen mutaciones. Los de la línea de comandos llaman a `main(argv)` y leen `capsys`; **uno** corre el programa en un proceso aparte para comprobar el código de salida real.

| Archivo de tests | Qué prueba | Datos |
|---|---|---|
| `test_kvpi_validacion.py` | RF-1 a RF-6: columnas, vacíos, texto no numérico, infinitos, repetidos (iguales, distintos, con vacíos), etiquetas con espacios, independencia del orden | Sintéticos de pocas filas |
| `test_kvpi_calculo.py` | RF-7 a RF-12: promedio, desvío n−1, `n_campanas`, CV, `min_campanas`, advertencias; criterio 2 con valores calculados a mano | Sintéticos |
| `test_kvpi_cobertura.py` | RF-20 a RF-22: cobertura, campaña sin datos con 0, `CAMPANA_CON_POCOS_DATOS`, lista de campañas esperadas | Sintéticos |
| `test_kvpi_union.py` | RF-13 y RF-14: orden del muestreo, columnas extra, plantas sin coordenadas o sin serie, `id` repetidos en el muestreo, ninguna en común | Sintéticos |
| `test_kvpi_cli.py` | RF-15 a RF-19: lectura, formato del archivo, no sobrescribir, pantalla, códigos de salida, no deja archivos | `main(argv)` con archivos en `tmp_path`; un caso en proceso aparte |
| `test_kvpi_golden.py` | Criterios 3 y 4: la serie real reproduce `KVPI_mean` y `KVPI_std` publicados; sin repetidos ni vacíos; `kvpi` → `mapa` → `analizar` da 16 "Mantener" y 19 "Intervenir" | `tests/golden/` |

## 6. Riesgos

1. **La serie real no está en el repositorio.** Está suelta en el directorio raíz; sin moverla a `tests/golden/` con su procedencia (C12), los criterios 3 y 4 no se pueden probar. Se pide permiso antes de moverla.
2. **Tipo del `id`.** Si la serie trae `4.0` y el muestreo `4`, la unión pierde plantas sin error. La advertencia `PLANTAS_SIN_SERIE` lo deja a la vista; la normalización queda como duda abierta.
3. **Valores atípicos de `KVPI`.** No se valida el rango (decidido en la spec); un valor absurdo entra al promedio sin aviso.
4. **`pandas` cambia entre versiones.** El desvío con `ddof=1` y el manejo de vacíos son estables, y el test con la serie real lo vigila.

## 7. Cobertura de requisitos

| RF | Módulo | Test |
|---|---|---|
| 1 a 6 | `kvpi` | `test_kvpi_validacion` |
| 7 a 12 | `kvpi` | `test_kvpi_calculo`, `test_kvpi_golden` |
| 13, 14 | `kvpi` | `test_kvpi_union` |
| 15, 19 | `flujo`, `cli` | `test_kvpi_cli` |
| 16 | `salida` | `test_kvpi_cli` |
| 17, 18 | `cli` | `test_kvpi_cli` (uno en proceso aparte) |
| 20 a 22 | `kvpi` | `test_kvpi_cobertura` |

## 8. Decisiones provisionales sobre los hallazgos menores

Todas siguen como dudas abiertas y se pueden cambiar:

- **C8.** Las columnas extra del muestreo (`left`, `top`, `right`, `bottom`, `row_index`, `col_index`) pasan al resultado, como pide RF-13.
- **C9.** `--min-campanas abc` da código 2 (rechazo de `argparse`) y no 1; es el mismo criterio que `--alfa` en la spec 003.
- **C11.** El criterio 4 se mantiene como está: la parte nueva que prueba es que `kvpi` produce un CSV equivalente al publicado; el resultado de `analizar` ya lo prueba la spec 003.
- **C12.** La serie real entra a `tests/golden/` junto con una nota de procedencia (fecha de exportación 24/10/2026, 954 filas, 159 plantas por 6 campañas); se pide permiso antes de moverla.
- **`id` con decimal.** Se comparan tal como se leen; no se normaliza `4.0` a `4`.
- **`KVPI_cv` con promedio negativo.** Se calcula con el signo que resulte; solo 0 lo deja vacío.
- **Rango de `KVPI`.** No se valida.
- **`mapa.html`.** Se propone agregarlo al `.gitignore` (fuera de esta spec).
