# Tareas — Spec 002

Reglas: una tarea a la vez, en orden. En cada una, primero se escribe el test y se lo ve fallar; después el código mínimo para que pase. Cada tarea apunta a menos de 30 minutos. Al terminar: correr toda la suite con avisos como errores (`-W error`), mostrar el resultado y marcar la casilla. Las tareas se numeran `T2.n` para no confundirlas con las de la spec 001.

## Datos de referencia

- [x] **T2.0. Resolver la procedencia del clima y copiar el archivo.** *(Necesita una decisión tuya; bloquea T2.16 a T2.18.)*
  - Cubre: hallazgo C15; prerrequisito de los criterios 2 a 7.
  - Hecho cuando: se sabe de dónde viene el archivo diario y bajo qué condiciones se puede usar; `tests/golden/clima_diario.csv` existe con `date`, `Tmax`, `Tmin` y una columna `origen` (2.604 filas, de `2019-01-01` a `2026-03-28`, con las 40 fechas faltantes sin rellenar), y la procedencia queda anotada en `AGENTS.md`. *Resuelta el 22/10/2026: 2.303 días idénticos al Excel de INTA y 301 no verificados; decisión de copiar el archivo completo marcando el origen de cada día.* Mientras no se haga, los tests de T2.16 a T2.18 se saltan con un motivo explícito.

## Parámetros y entrada

- [x] **T2.1. Validación de parámetros.** `clima_parametros.py`.
  - Cubre: RF-9.
  - Hecho cuando: los valores por defecto de la spec están definidos en un solo lugar; cada valor no permitido da `ErrorDeEntrada` que nombra los permitidos (`ventana_frio`, `cobertura_minima`, `max_hueco_dias`, umbrales, `rango_fisico`, `mes_inicio_temporada`, `meses_frio`, `campana`, `formato_fecha`); en modo "invierno", `meses_frio = (11, 12, 1, 2)` y `(5, 7, 8)` dan un error que dice que solo se admiten ventanas continuas dentro de un año calendario, mientras que en modo "temporada" se aceptan.

- [x] **T2.2. Columnas, tabla vacía y temperaturas numéricas.** `clima_entrada.py`.
  - Cubre: RF-1, RF-3.
  - Hecho cuando: falta `date`, `Tmax` o `Tmin`, o tabla vacía, o temperatura con texto, dan `ErrorDeEntrada` que nombra el problema; los valores vacíos no son error; las columnas extra (`Tmedia`, `horas_frio`) no afectan; con coma decimal el error menciona esa causa posible.

- [x] **T2.3. Fechas.**
  - Cubre: RF-2.
  - Hecho cuando: `2019-01-02`, `2019-01-02 13:45` y `2019-01-02T00:00:00-03:00` dan el día 2 de enero; una columna ya convertida a fecha se acepta; `01/02/2019` da error (no se interpreta) y con `formato_fecha="%d/%m/%Y"` da el 1 de febrero; fechas vacías o ilegibles dan error con la cantidad y un ejemplo.

- [x] **T2.4. Fechas repetidas.**
  - Cubre: RF-4.
  - Hecho cuando: las filas repetidas con los mismos `Tmax` y `Tmin` se reducen a una con la advertencia `FECHA_DUPLICADA` y la cantidad (aunque difieran en una columna extra); la misma fecha con `Tmax` o `Tmin` distintos da error que nombra hasta 10 fechas.

- [x] **T2.5. `Tmax < Tmin` y rango físico.**
  - Cubre: RF-5, RF-6.
  - Hecho cuando: `Tmax < Tmin` da error con la cantidad de días y las primeras 10 fechas; `Tmax = Tmin` es válido; un valor como −999 da error con la cantidad; `rango_fisico` es un parámetro.

- [x] **T2.6. Días faltantes y orden.**
  - Cubre: RF-7, RF-8.
  - Hecho cuando: un día con `Tmax` o `Tmin` vacío queda marcado como faltante; una tabla desordenada da el mismo resultado que ordenada; la tabla de entrada no se modifica; `preparar_clima` devuelve la tabla normalizada y las advertencias de la entrada.

## Cálculo diario

- [x] **T2.7. GDD diario y horas de frío.** `clima_calculo.py`.
  - Cubre: RF-10, RF-11.
  - Hecho cuando: `GDD_diario = max(Tmedia − tbase, 0)` y las horas de coseno coinciden con valores calculados a mano (por ejemplo, `Tmax = 10`, `Tmin = 0`, umbral 7: 15,14 h); `Tmax ≤ umbral` da 24 h; `Tmin ≥ umbral` da 0 h; `Tmax = Tmin = umbral` da 24 h; el resultado coincide con una copia independiente de la función escalar del notebook sobre 1.000 pares aleatorios.

## Períodos

- [x] **T2.8. Temporadas, ventanas y días esperados.** `clima_periodos.py`.
  - Cubre: RF-12, RF-13.
  - Hecho cuando: la temporada empieza el 1 de `mes_inicio_temporada`, dura 12 meses y se etiqueta con el año de inicio; en modo "invierno" la ventana de cada año tiene 123 días de mayo a agosto; en modo "temporada" la ventana mezcla mayo–junio de un año con julio–agosto del anterior; el día esperado de una temporada que incluye el 29 de febrero es 366.

- [x] **T2.9. Cobertura, hueco máximo y período completo.**
  - Cubre: RF-14, RF-15, RF-16.
  - Hecho cuando: por período salen días disponibles, esperados (incluidos los que caen fuera del rango de los datos), cobertura y hueco máximo; con 7 de 25 días y `cobertura_minima=0,28` el período es completo (comparación por división; multiplicar daría incompleto por el redondeo de `0,28 × 25`); `max_hueco_dias=None` desactiva el límite; un hueco de 8 días con límite 7 hace incompleto un período con cobertura 98 %; un período sin ningún día disponible no aparece.

## Resultado

- [x] **T2.10. GDD por temporada.** `clima.py`.
  - Cubre: RF-17, RF-18.
  - Hecho cuando: `calcular_clima` devuelve la tabla `gdd` con `temporada`, `GDD_total` y las columnas de cobertura; el valor se calcula aunque el período sea incompleto; cada temporada incompleta genera `PERIODO_INCOMPLETO` con un mensaje que empieza con "GDD, temporada N" y trae cobertura y hueco.

- [x] **T2.11. Horas de frío y estado.**
  - Cubre: RF-19, RF-20, RF-21.
  - Hecho cuando: la tabla `frio` trae `periodo`, `Horas_Frio` y `estado_frio`; el estado solo se asigna a ventanas completas ("Óptimo" ≥ 950, "Adecuado" ≥ 750, "Deficiente" en el resto) y sale de `ESTADOS_FRIO` de la spec 001; una ventana incompleta queda sin estado y avisa `PERIODO_INCOMPLETO` ("Frío, ventana N…"); una ventana completa con cobertura menor que 1 avisa `COBERTURA_PARCIAL`.

- [x] **T2.12. Salida completa y modo de reproducción.**
  - Cubre: RF-26, RF-27.
  - Hecho cuando: `ResultadoClima` devuelve ambas tablas y las advertencias en orden (las de la entrada, luego por período cronológico, GDD antes que frío); con `ventana_frio="temporada"`, `cobertura_minima=0` y `max_hueco_dias=None`, una serie sintética de varios años reproduce que cada ventana suma mayo–junio de un año y julio–agosto del anterior, y que las temporadas de los bordes quedan clasificadas.

## Última campaña

- [x] **T2.13. Última campaña clasificable.** `campana.py`.
  - Cubre: RF-22, RF-24, RF-28.
  - Hecho cuando: `estado_frio_de_campana` sin `campana` devuelve el estado de la ventana clasificable más reciente, con período, horas, cobertura y hueco máximo, y avisa `CAMPANA_NO_INDICADA` nombrando el período usado; si ninguna es clasificable devuelve estado vacío y `SIN_PERIODO_CLASIFICABLE`.

- [x] **T2.14. Campaña indicada.**
  - Cubre: RF-23, RF-25.
  - Hecho cuando: con `campana=Y` usa el período de etiqueta Y (en modo "invierno", el invierno de Y; en "temporada", la temporada Y) y no avisa `CAMPANA_NO_INDICADA`; si ese período no existe o no es clasificable da `ErrorDeEntrada` que dice el motivo (sin datos, o su cobertura y hueco); una ventana elegida con cobertura menor que 1 avisa `COBERTURA_PARCIAL`.

- [x] **T2.15. Integración con la spec 001.**
  - Cubre: criterio 7 (con datos sintéticos); consistencia de los textos de estado (hallazgo C12).
  - Hecho cuando: el estado devuelto por `estado_frio_de_campana` lo acepta `analizar(..., estado_frio_ultima_campana=...)` sin error, para los tres estados posibles; un estado vacío llega a `analizar()` y produce `SIN_ESTADO_FRIO`.

## Verificación con datos reales *(requieren T2.0)*

- [x] **T2.16. Reproducir el notebook (criterio 2).** `test_clima_golden.py`.
  - Cubre: RF-27, criterio 2.
  - Hecho cuando: con `ventana_frio="temporada"`, `cobertura_minima=0` y `max_hueco_dias=None`, el GDD por temporada (2018 a 2025) coincide con `gdd_por_campana.csv` con diferencia menor que 1e-9, y las horas de frío (331,7 / 921,5 / 949,8 / 1.115,2 / 839,3 / 1.009,0 / 1.036,1 / 439,2) y sus estados coinciden con `horas_frio_por_campana.csv` con tolerancia 1e-6.

- [x] **T2.17. Invierno por defecto (criterios 3 y 4).**
  - Cubre: RF-19, RF-20, criterios 3 y 4.
  - Hecho cuando: las horas son 956,5 / 853,5 / 925,0 / 1.090,4 / 853,5 / 1.128,8 para 2019 a 2024 (123 días) y 834,2 para 2025 (119 de 123 días), con tolerancia 0,05 h; los estados son "Óptimo" en 2019, 2022 y 2024 y "Adecuado" en 2020, 2021, 2023 y 2025; ninguno es "Deficiente".

- [x] **T2.18. Campaña, GDD e integración (criterios 5, 6 y 7).**
  - Cubre: RF-18, RF-22, RF-23, RF-28, criterios 5 a 7.
  - Hecho cuando: sin `campana` el resultado es el invierno 2025 ("Adecuado", 0,9675 de cobertura, hueco 4, con `CAMPANA_NO_INDICADA`); con `campana=2024` es el invierno 2024 ("Óptimo", 1.128,8 h, sin esa advertencia); las temporadas de GDD 2019, 2020, 2021, 2023 y 2024 son completas y la 2022 (cobertura 0,901, hueco de 34 días), la 2018 y la 2025 son incompletas; pasar cualquiera de los dos estados a `analizar()` sobre el lote de referencia da 16 "Mantener" y 19 "Intervenir".

## Cierre

- [x] **T2.19. Validación final.**
  - Cubre: criterio 8 de la spec (cada RF con test).
  - Hecho cuando: existe `validacion.md` con la matriz de los 28 RF contra sus tests y el estado de cada criterio; la suite completa pasa con `-W error` **sin tests saltados** en `test_clima_golden.py`; se hicieron mutaciones (borde de la cobertura, formato de fecha, `max_hueco_dias`, valor por defecto de `ventana_frio`) y cada una hace fallar al menos un test; el trabajo queda commiteado.

## Notas

- Orden de dependencia: T2.1 a T2.6 (entrada) → T2.7 (cálculo) → T2.8 y T2.9 (períodos) → T2.10 a T2.12 (resultado) → T2.13 a T2.15 (campaña) → T2.16 a T2.18 (datos reales) → T2.19.
- T2.0 es independiente del resto y puede hacerse en cualquier momento antes de T2.16; conviene resolverla pronto para no acumular tests saltados.
- Las dudas abiertas de la clarificación (hallazgos medios y menores) no tienen tarea: se resuelven con los comportamientos provisionales de la sección 8 del plan.
