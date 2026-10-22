# Plan — Spec 002

Estado: BORRADOR. Sin código. Lee: `docs/constitution.md`, `spec.md` (RF-1 a RF-28) y `clarificacion.md`. Los hallazgos menores quedan como dudas abiertas; donde el plan necesita una decisión sobre uno de ellos, la toma de forma provisional y lo dice (sección 8).

## 1. Idea general

Un pipeline sobre una tabla diaria de temperaturas. Todo es núcleo (sin archivos) y usa solo pandas y numpy: **no hacen falta dependencias nuevas** (constitución #1).

```
tabla diaria ──► clima_entrada ──► días válidos ──► clima_calculo ──► GDD y horas por día
(date, Tmax, Tmin)  RF-1..8                          RF-10, 11              │
                                                                            ▼
parámetros ──► validación (RF-9)     clima_periodos: períodos, cobertura, hueco, completo (RF-12..16)
                                                                            │
                                                                            ▼
                                              clima.calcular_clima ──► ResultadoClima (RF-17..21, 26, 27)
                                                                            │
                                                                            ▼
                                              campana.estado_frio_de_campana ──► estado (RF-22..25, 28)
                                                                            │
                                                                            ▼
                                                   analizar(..., estado_frio_ultima_campana=estado)   [spec 001]
```

## 2. Módulos

| Módulo | Qué hace | RF que cubre |
|---|---|---|
| `kiwitracking/clima_entrada.py` | Valida y normaliza la tabla diaria: columnas, fechas (ISO o `formato_fecha`), numéricos, duplicados, `Tmax < Tmin`, rango físico, días faltantes, orden | RF-1 a RF-8 |
| `kiwitracking/clima_parametros.py` | Valida los parámetros (`ventana_frio`, cobertura, hueco, umbrales, meses, `campana`…) y define sus valores por defecto | RF-9 |
| `kiwitracking/clima_calculo.py` | GDD diario y horas de frío diarias (modelo de coseno), vectorizados | RF-10, RF-11 |
| `kiwitracking/clima_periodos.py` | Asigna cada día a su temporada o ventana de frío, arma los días esperados y calcula disponibles, cobertura, hueco máximo y `completo` | RF-12 a RF-16 |
| `kiwitracking/clima.py` | `calcular_clima(...)`: une todo y devuelve el `ResultadoClima` (tabla de GDD, tabla de frío, advertencias) | RF-17 a RF-21, RF-26, RF-27 |
| `kiwitracking/campana.py` | `estado_frio_de_campana(...)`: elige el período de la campaña indicada o el clasificable más reciente | RF-22 a RF-25, RF-28 |

No se ofrece lectura de archivos en esta iteración (el requisito no funcional dice "si se ofrece"): los tests leen el CSV con pandas. Cada módulo depende solo de los anteriores en la lista.

## 3. Modelo de datos

**Entrada.** `DataFrame` con `date`, `Tmax`, `Tmin`; las demás columnas se ignoran. Parámetros como argumentos con nombre y sus valores por defecto de la spec.

**Salida: `ResultadoClima`.**
- `gdd`: una fila por temporada. Columnas: `temporada` (año de inicio), `GDD_total`, `dias_disponibles`, `dias_esperados`, `cobertura`, `hueco_maximo`, `completo`.
- `frio`: una fila por ventana. Columnas: `periodo` (año de la etiqueta), `Horas_Frio`, `estado_frio` (vacío si no es completo), `dias_disponibles`, `dias_esperados`, `cobertura`, `hueco_maximo`, `completo`.
- `advertencias`: `list[Advertencia]` (el mismo tipo de la spec 001). Códigos: `FECHA_DUPLICADA`, `PERIODO_INCOMPLETO`, `COBERTURA_PARCIAL`.
- `ventana_frio`: el modo usado, para que `campana.py` redacte bien sus mensajes.

Los nombres `GDD_total`, `Horas_Frio` y `estado_frio` son los de los CSV del notebook, así los criterios 2 y 3 se comparan sin renombrar nada; en la tabla de frío la etiqueta se llama `periodo` (y no `temporada`) porque en modo "invierno" no es una temporada.

**Salida: `EstadoCampana`.** `estado` (`str | None`), `periodo`, `horas`, `cobertura`, `hueco_maximo` y `advertencias` (`CAMPANA_NO_INDICADA`, `COBERTURA_PARCIAL`, `SIN_PERIODO_CLASIFICABLE`).

## 4. Decisiones técnicas

| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D1 | Fechas de texto: se toman los 10 primeros caracteres y se leen con formato exacto `%Y-%m-%d`; con `formato_fecha` se usa ese formato. Las columnas ya convertidas se normalizan a día | Que pandas infiera el formato; `format="ISO8601"` con zona horaria | Es lo único que cumple "tomar el día tal como está escrito" y "nunca inferir": una conversión de zona puede mover el día y la inferencia confunde `dd/mm` con `mm/dd` |
| D2 | Un día es "disponible" si tiene `Tmax` y `Tmin` no vacíos; los demás días del período esperado cuentan como faltantes, tengan fila o no | Interpolar o extrapolar | Está fuera de alcance rellenar datos |
| D3 | Los días esperados se arman con `pd.date_range` del calendario (366 en año bisiesto, 123 de mayo a agosto) | Contar 365 o 123 fijos | Los años bisiestos y los períodos truncados lo exigen |
| D4 | La cobertura se compara **dividiendo** (`disponibles / esperados >= cobertura_minima`) | Multiplicar `cobertura_minima × esperados` | En el borde exacto, multiplicar puede rechazar un período que cumple: `0,28 × 25 = 7,000000000000001`, así que 7 de 25 días con mínimo 0,28 daría incompleto (hay 54 casos así entre 2 y 400 días); hay un test del borde |
| D5 | El hueco máximo se calcula con una máscara booleana sobre los días esperados y una búsqueda de la racha más larga con numpy | Un bucle día por día | Mismo resultado, más corto y fácil de probar; el volumen es chico en cualquier caso |
| D6 | Horas de frío vectorizadas con `numpy.where` y `arccos` recortado; un test compara contra una copia independiente de la función escalar del notebook | Aplicar la función escalar fila por fila | Es el mismo cálculo, y la comparación evita errores de transcripción |
| D7 | Un período sin ningún día disponible no aparece (sus etiquetas salen de los días disponibles) | Mostrarlo con cobertura 0 | Lo pide RF-16 |
| D8 | Los textos de estado salen de `ESTADOS_FRIO` de la spec 001 (`validacion.py`) | Escribirlos de nuevo en el módulo de clima | Una sola definición, para que "Óptimo" nunca difiera entre las dos specs |
| D9 | Los duplicados de fecha se comparan solo por `date`, `Tmax` y `Tmin`; las columnas extra se ignoran | Generalizar `descartar_duplicados` de la spec 001 | Esa función compara todas las columnas y devuelve otro código; tocarla arriesga lo ya validado |
| D10 | `campana.py` recibe un `ResultadoClima` ya calculado | Que cada llamada recalcule el clima | Se separa "calcular" de "elegir", y se prueba la elección con tablas armadas a mano |

## 5. Estrategia de pruebas

Mismas reglas de la spec 001: cada RF tiene un test que lleva su número (`test_rfN_...`), el test se escribe primero y se ve fallar, y al cerrar cada cambio se hacen mutaciones.

| Archivo de tests | Qué prueba | Datos |
|---|---|---|
| `test_clima_entrada.py` | RF-1 a RF-8: columnas, fechas ISO y con `formato_fecha`, fechas vacías, duplicados, `Tmax < Tmin`, rango físico, orden | Sintéticos de pocas filas |
| `test_clima_parametros.py` | RF-9, incluido `meses_frio` que cruza el fin de año en modo "invierno" | Sin datos |
| `test_clima_calculo.py` | RF-10, RF-11: valores calculados a mano, borde `Tmax = Tmin = umbral`, comparación con la función del notebook | Sintéticos |
| `test_clima_periodos.py` | RF-12 a RF-16: temporada, ventana, años bisiestos, cobertura exacta en el borde, hueco máximo | Sintéticos |
| `test_clima.py` | RF-17 a RF-21, RF-26, RF-27 con varios años sintéticos | Sintéticos |
| `test_campana.py` | RF-22 a RF-25, RF-28 | Tablas de `ResultadoClima` armadas a mano |
| `test_clima_golden.py` | Criterios 2 a 7 con el clima real | Archivo diario en `tests/golden/` |

**Los datos de referencia no están todavía en el repositorio.** El archivo de clima está en la carpeta de otro proyecto y su procedencia es una duda abierta (hallazgo C15). Hasta que la resuelvas, `test_clima_golden.py` se salta con un motivo explícito, y **la validación final no se da por cumplida mientras esos tests estén saltados**. Cuando se copie, irá con solo `date`, `Tmax` y `Tmin`.

## 6. Riesgos

1. **Golden pendiente (C15).** Sin el archivo no se puede verificar el criterio 2 (reproducir el notebook), que es el que más valor tiene.
2. **pandas 3 y las columnas de texto.** El tipo de texto por defecto cambió; los tests de fechas cubren columnas de texto, de fecha ya convertida y con valores vacíos.
3. **Etiquetas en modo "temporada".** Mezcla dos inviernos por diseño; los tests del RF-27 fijan los valores del notebook, incluidos los de los bordes.
4. **Los estados dependen del modelo de coseno (observación O1).** No es un riesgo de implementación, pero los tests solo prueban que el código aplica el modelo, no que el modelo sea correcto.

## 7. Cobertura de requisitos

| RF | Módulo | Test |
|---|---|---|
| 1 a 8 | `clima_entrada` | `test_clima_entrada` |
| 9 | `clima_parametros` | `test_clima_parametros` |
| 10, 11 | `clima_calculo` | `test_clima_calculo` |
| 12 a 16 | `clima_periodos` | `test_clima_periodos` |
| 17 a 21, 26, 27 | `clima` | `test_clima`, `test_clima_golden` |
| 22 a 25, 28 | `campana` | `test_campana`, `test_clima_golden` |

## 8. Decisiones provisionales sobre los hallazgos menores

Todas siguen como dudas abiertas y se pueden cambiar:

- **C3.** Las temporadas de GDD completas con cobertura menor que 1 **no** avisan (RF-18 solo cubre las incompletas), como está escrito. Queda la asimetría con el frío.
- **C4.** El código `PERIODO_INCOMPLETO` es el mismo, pero el mensaje empieza con "GDD, temporada 2022" o "Frío, ventana 2022" para distinguirlos.
- **C6.** Los duplicados se comparan solo por `date`, `Tmax` y `Tmin` (D9).
- **C8.** Con `Tmax = Tmin = umbral` se aplica primero "24 horas si `Tmax ≤ umbral`", como el notebook.
- **C9.** Los nombres de columnas son los de la sección 3.
- **C10.** Una fecha sin fila y una con valor vacío cuentan igual como faltantes.
- **C13.** Si una columna de temperatura es de texto y varios valores tienen coma decimal, el error lo menciona como posible causa.
- **C14.** Las advertencias por período se ordenan por etiqueta y, a igual etiqueta, la de GDD antes que la de frío.
