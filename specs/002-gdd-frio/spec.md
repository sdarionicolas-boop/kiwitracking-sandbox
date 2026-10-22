# Spec 002 — GDD y horas de frío desde temperaturas diarias

Estado: BORRADOR (clarificación hecha; 3 hallazgos graves resueltos, el resto como dudas abiertas)

## Contexto y objetivo
La spec 001 recibe el estado de frío de la última campaña ("Deficiente", "Adecuado" u "Óptimo") como un texto escrito a mano. Esta spec lo calcula: a partir de temperaturas diarias (Tmax/Tmin) obtiene los grados día de crecimiento (GDD) por temporada y las horas de frío por invierno con el modelo de coseno, informa qué tan completos están los datos de cada período, y elige la última campaña que se puede clasificar con confianza.

Una revisión del cálculo original (notebook 03) encontró que la "temporada" de julio parte la ventana de frío (mayo–agosto) entre dos temporadas, de modo que cada una suma partes de dos inviernos distintos, y que las temporadas de los bordes del registro quedan truncadas. Los dos únicos "Deficiente" publicados (2018 y 2025) son consecuencia de esos bordes. Esta spec calcula el frío por invierno completo por defecto y conserva el cálculo original como una opción para poder reproducirlo.

Correspondencia entre campaña y período: la campaña `Y` (la que empieza en julio de `Y`, por ejemplo la 2024/25) se corresponde con el período de etiqueta `Y`. En modo "invierno" es el invierno de mayo–agosto de `Y`, que precede a esa campaña; en modo "temporada", la temporada `Y`.

## Usuarios / actores
- **Investigador/a** que corre el análisis y decide qué estado de frío usar.
- **Técnico/a de campo** que lee el estado de frío y el GDD de cada campaña.

## Historias de usuario
- **H1.** Como investigador/a, quiero calcular las horas de frío por invierno completo y no mezclando dos inviernos, para que el estado de frío refleje un solo período de dormancia.
- **H2.** Como investigador/a, quiero saber cuántos días de datos tiene cada período y cuál fue el hueco más largo, para no confiar en un valor armado con datos incompletos.
- **H3.** Como investigador/a, quiero que el sistema elija la última campaña clasificable y me diga cuál usó, para alimentar el análisis de la spec 001 sin escribir el estado a mano.
- **H4.** Como investigador/a, quiero poder reproducir el cálculo del notebook original, para comparar con lo publicado.
- **H5.** Como investigador/a, quiero que los datos defectuosos produzcan errores o advertencias claras.

## Entradas
Tabla diaria con `date`, `Tmax` y `Tmin`. Las demás columnas se ignoran, incluidas `Tmedia` y `horas_frio` si vienen precalculadas.

Parámetros opcionales, con su valor por defecto:
- `ventana_frio`: `"invierno"` (por defecto) o `"temporada"`.
- `tbase`: 10 °C (GDD).
- `umbral_frio`: 7 °C (horas de frío).
- `meses_frio`: mayo a agosto (5, 6, 7, 8).
- `mes_inicio_temporada`: 7 (julio).
- `cobertura_minima`: 0,9.
- `max_hueco_dias`: 7 (`None` = sin límite).
- `umbral_optimo`: 950 h; `umbral_adecuado`: 750 h.
- `rango_fisico`: (−60, 60) °C.
- `formato_fecha`: `None` (por defecto, solo `AAAA-MM-DD`) o un formato explícito, por ejemplo `"%d/%m/%Y"` (ver RF-2).
- `campana`: año de inicio de la campaña a la que corresponde el estado de frío (ver RF-23); por defecto, el período clasificable más reciente.

## Requisitos funcionales

**Validación de la entrada**
- **RF-1.** SI falta alguna columna obligatoria (`date`, `Tmax`, `Tmin`) o la tabla está vacía, ENTONCES el sistema DEBE detenerse con un error que nombre el problema.
- **RF-2.** El sistema DEBE leer `date` como fecha en formato `AAAA-MM-DD`, con o sin hora o zona horaria, o como fecha ya convertida; cuando se indique `formato_fecha`, DEBE leerla con ese formato. El sistema NO DEBE inferir el formato. Cuando una fecha trae hora o zona horaria, DEBE tomar el día tal como está escrito, sin convertir de zona. SI hay fechas vacías o que no se pueden leer, ENTONCES DEBE detenerse con un error que diga cuántas son y muestre un ejemplo.
- **RF-3.** SI `Tmax` o `Tmin` contienen texto no numérico, ENTONCES el sistema DEBE detenerse con un error que nombre la columna. Los valores vacíos no son un error (RF-7).
- **RF-4.** SI hay fechas repetidas con todos los valores iguales, ENTONCES el sistema DEBE conservar una sola y registrar una advertencia `FECHA_DUPLICADA` con la cantidad descartada. SI una fecha se repite con valores distintos, ENTONCES DEBE detenerse con un error que nombre hasta 10 fechas en conflicto.
- **RF-5.** SI algún día tiene `Tmax` menor que `Tmin`, ENTONCES el sistema DEBE detenerse con un error que diga cuántos días son y nombre las primeras 10 fechas.
- **RF-6.** SI hay temperaturas fuera de `rango_fisico`, ENTONCES el sistema DEBE detenerse con un error que diga cuántas son.
- **RF-7.** Un día con `Tmax` o `Tmin` vacío DEBE contar como día faltante: no aporta GDD ni horas de frío, reduce la cobertura y entra en el cálculo del hueco máximo.
- **RF-8.** El resultado NO DEBE depender del orden de las filas de entrada.
- **RF-9.** SI un parámetro tiene un valor no permitido, ENTONCES el sistema DEBE detenerse con un error que nombre los valores permitidos. Son no permitidos: `ventana_frio` distinto de "invierno" o "temporada"; `cobertura_minima` fuera de [0, 1]; `max_hueco_dias` negativo o no entero (salvo `None`); `umbral_optimo` menor o igual que `umbral_adecuado`; `rango_fisico` con el mínimo no menor que el máximo; `mes_inicio_temporada` fuera de 1 a 12; `meses_frio` vacío o con meses fuera de 1 a 12; `campana` que no sea un entero (salvo `None`); `formato_fecha` que no sea texto (salvo `None`). Además, CUANDO `ventana_frio` sea "invierno", `meses_frio` DEBE ser una serie de meses consecutivos dentro de un mismo año calendario: SI cruza el fin de año o tiene saltos (por ejemplo, 11, 12, 1, 2), ENTONCES el sistema DEBE detenerse con un error que explique que esta versión solo admite ventanas continuas dentro de un año calendario.

**Cálculo diario**
- **RF-10.** El sistema DEBE calcular, por cada día disponible, `Tmedia = (Tmax + Tmin) / 2` y `GDD_diario = max(Tmedia − tbase, 0)`.
- **RF-11.** El sistema DEBE calcular las horas de frío diarias con el modelo de coseno: 24 si `Tmax ≤ umbral_frio`; 0 si `Tmin ≥ umbral_frio`; en otro caso, `(24 / π) × (π − θ)` con `θ = arccos(clip((umbral_frio − Tmedia) / amp, −1, 1))` y `amp = (Tmax − Tmin) / 2`.

**Períodos y cobertura**
- **RF-12.** Una temporada DEBE empezar el día 1 de `mes_inicio_temporada`, durar 12 meses y llevar como etiqueta el año en que empieza.
- **RF-13.** CUANDO `ventana_frio` sea "invierno", el sistema DEBE agrupar las horas de frío por año calendario, usando los días de `meses_frio` de ese año; CUANDO sea "temporada", DEBE agruparlas por temporada, usando los días de `meses_frio` que caen dentro de cada una (cálculo del notebook original, que mezcla partes de dos inviernos).
- **RF-14.** Para cada período, el sistema DEBE informar los días disponibles, los días esperados (todos los que el período tendría completo, también los que quedan fuera del rango de datos), la cobertura (`disponibles / esperados`) y el hueco máximo (la mayor racha de días esperados consecutivos sin dato, incluidos los que quedan fuera del rango de datos).
- **RF-15.** Un período DEBE ser `completo` si su cobertura es mayor o igual que `cobertura_minima` Y (`max_hueco_dias` es `None` o su hueco máximo es menor o igual que `max_hueco_dias`).
- **RF-16.** Un período sin ningún día de datos NO DEBE aparecer en el resultado.

**GDD**
- **RF-17.** El sistema DEBE devolver, por temporada, `GDD_total` (suma del GDD diario de los días disponibles) junto con la información de RF-14 y RF-15. El valor DEBE calcularse aunque el período no sea completo.
- **RF-18.** SI una temporada no es completa, ENTONCES el sistema DEBE registrar una advertencia `PERIODO_INCOMPLETO` que nombre el período, su cobertura y su hueco máximo.

**Horas de frío**
- **RF-19.** El sistema DEBE devolver, por ventana (RF-13), `Horas_Frio` (suma de las horas diarias de los días disponibles) junto con la información de RF-14 y RF-15.
- **RF-20.** CUANDO una ventana sea completa, el sistema DEBE asignar `estado_frio`: "Óptimo" si `Horas_Frio ≥ umbral_optimo`; "Adecuado" si `≥ umbral_adecuado`; "Deficiente" en el resto. SI no es completa, ENTONCES `estado_frio` DEBE quedar vacío y DEBE registrarse una advertencia `PERIODO_INCOMPLETO`.
- **RF-21.** CUANDO una ventana sea completa pero su cobertura sea menor que 1, el sistema DEBE registrar una advertencia `COBERTURA_PARCIAL` con la cobertura.

**Última campaña**
- **RF-22.** El sistema DEBE ofrecer una función que devuelva el estado de frío de la última campaña: el de la ventana que corresponde a `campana` (RF-23) o, si no se indica, el de la ventana clasificable más reciente (la de mayor etiqueta con `estado_frio` no vacío). El resultado DEBE incluir el estado (utilizable como `estado_frio_ultima_campana` de la spec 001), la etiqueta del período, las horas, la cobertura y el hueco máximo.
- **RF-23.** CUANDO se indique `campana`, el sistema DEBE usar el período de etiqueta `campana`: en modo "invierno", el invierno de ese año, que precede a la campaña `campana`/`campana`+1; en modo "temporada", la temporada de ese año. SI ese período no existe o no es clasificable, ENTONCES DEBE detenerse con un error que diga el motivo (sin datos, o su cobertura y su hueco máximo).
- **RF-24.** SI ninguna ventana es clasificable, ENTONCES la función DEBE devolver el estado vacío y registrar una advertencia `SIN_PERIODO_CLASIFICABLE`.
- **RF-25.** CUANDO la ventana elegida tenga cobertura menor que 1, la función DEBE registrar la advertencia `COBERTURA_PARCIAL` (RF-21).
- **RF-28.** CUANDO no se indique `campana` y la función elija un período, ENTONCES DEBE registrar la advertencia `CAMPANA_NO_INDICADA`, que nombre el período usado y diga que puede ser posterior a la última campaña analizada.

**Salida**
- **RF-26.** El sistema DEBE devolver una tabla de GDD por temporada, una tabla de frío por ventana y la lista de advertencias, con las de la entrada primero y después las de cada período en orden cronológico.

**Reproducción del cálculo original**
- **RF-27.** CUANDO `ventana_frio` sea "temporada", `cobertura_minima` sea 0 y `max_hueco_dias` sea `None`, el sistema DEBE reproducir las horas de frío y los estados del notebook original, incluidas las temporadas truncadas de los extremos del registro.

## Requisitos no funcionales
- El núcleo no lee ni escribe archivos ni contiene rutas fijas (constitución #6, #9).
- El núcleo no modifica la tabla de entrada.
- Todos los umbrales y valores de la sección Entradas son parámetros explícitos con sus valores por defecto (constitución #7).
- La lectura de archivos, si se ofrece, vive en la capa de entrada y salida y respeta la constitución #8 (UTF-8).

## Casos límite
- `meses_frio` que cruza el fin de año en modo "invierno": error (RF-9); en modo "temporada" se admite, porque ahí la mezcla de períodos es lo que se reproduce.
- Fechas con hora o zona horaria: se toma el día tal como está escrito (RF-2).
- Un día con `Tmax` igual a `Tmin`: es válido (amplitud cero); da 24 h de frío si `Tmax ≤ umbral_frio` y 0 en otro caso.
- Años bisiestos: los días esperados de la temporada y de la ventana salen del calendario (366 o 365 días; 123 días de mayo a agosto).
- Datos que terminan a mitad de un invierno: ese invierno aparece con cobertura baja, no se clasifica y la última campaña es el invierno completo anterior.
- Datos que empiezan después del 1 de mayo: ese primer invierno aparece incompleto.
- Una sola fila de datos: se calcula, y todos los períodos resultan incompletos.
- `cobertura_minima` = 1: solo los períodos sin ningún día faltante son completos.

## Fuera de alcance
- Rellenar o estimar los días faltantes (interpolación, climatología): los huecos se detectan e informan, no se inventan datos.
- Detección de anomalías climáticas (Isolation Forest).
- Descarga de datos climáticos desde INTA u otras fuentes.
- Otros modelos de frío (Utah, Dinámico) y datos horarios.
- Validar los umbrales para otros cultivos o cultivares (son parámetros, no están validados).
- Conectar el clima dentro de `analizar()`: la función de RF-22 devuelve el estado y se pasa a `analizar()` por separado.
- Gráficos y mapas de GDD o frío.
- Predecir rendimiento (constitución #10).

## Criterios de finalización
1. Todos los tests `RF-n` pasan, con avisos tratados como errores.
2. **Reproduce el notebook** con `ventana_frio="temporada"`, `cobertura_minima=0` y `max_hueco_dias=None`: GDD por temporada (2018 a 2025) con diferencia menor que 1e-9 respecto de `gdd_por_campana.csv`, y horas de frío (331,7 / 921,5 / 949,8 / 1.115,2 / 839,3 / 1.009,0 / 1.036,1 / 439,2) con tolerancia 1e-6 respecto de `horas_frio_por_campana.csv`.
3. **Invierno por defecto:** 956,5 / 853,5 / 925,0 / 1.090,4 / 853,5 / 1.128,8 h para 2019 a 2024 (123 días cada uno) y 834,2 h para 2025 con 119 de 123 días, tolerancia 0,05 h.
4. **Estados por invierno:** "Óptimo" en 2019, 2022 y 2024; "Adecuado" en 2020, 2021, 2023 y 2025; ninguno "Deficiente".
5. **Última campaña:** sin indicar `campana`, el invierno 2025 (el clasificable más reciente), "Adecuado", cobertura 119/123 (0,9675), hueco máximo de 4 días y la advertencia `CAMPANA_NO_INDICADA`. Con `campana=2024`, el invierno 2024: "Óptimo", 1.128,8 h, cobertura 1 y sin esa advertencia.
6. **GDD por defecto:** las temporadas 2019, 2020, 2021, 2023 y 2024 son completas; la 2022 es incompleta por su hueco de 34 días (aunque su cobertura es 0,901); la 2018 (cobertura 0,496) y la 2025 (cobertura 0,742) son incompletas.
7. **Integración con la spec 001:** pasar el estado de RF-22 (tanto el de `campana=2024` como el del invierno más reciente) a `analizar()` sobre el lote de referencia da 16 "Mantener" y 19 "Intervenir" (valor por defecto de `escalar_std`), en lugar de los 0 "Mantener" publicados con el frío "Deficiente".
8. Cada requisito tiene al menos un test asociado (fase de Validación).

## Dudas abiertas
- **[NECESITA ACLARACIÓN]** Reproducir el notebook exige `max_hueco_dias=None` además de `cobertura_minima=0` (RF-27): con el límite de 7 días, la temporada 2018 (hueco de 62 días en la ventana) queda sin clasificar aunque la cobertura mínima sea 0. En la entrevista se había hablado solo de `cobertura_minima=0`.
- **[NECESITA ACLARACIÓN]** Los períodos sin ningún día de datos no aparecen (RF-16). Alternativa: aparecer con cobertura 0 y estado vacío.
- **[NECESITA ACLARACIÓN]** La cobertura y el hueco máximo cuentan como faltantes los días que quedan fuera del rango de los datos (RF-14). Es lo que marca incompletas a las temporadas de los bordes.
- **[NECESITA ACLARACIÓN]** El criterio de completitud es el mismo para GDD y para frío (RF-15), aunque un hueco de verano pesa más en el GDD que uno de otoño. Un criterio distinto por tipo de período queda para una versión posterior.
- **[NECESITA ACLARACIÓN]** El rango físico por defecto de (−60, 60) °C y el valor por defecto de `max_hueco_dias` (7) no tienen fundamento publicado: salen de la entrevista.
- **[NECESITA ACLARACIÓN]** `mes_inicio_temporada=7` se usa para el GDD y para la ventana "temporada"; para otro clima o cultivo puede no ser adecuado.
- **[NECESITA ACLARACIÓN]** Las horas y el GDD de los períodos incompletos se calculan sobre los días disponibles, sin extrapolar; el valor está subestimado y la advertencia es la única señal.

## Historial de cambios
- **Clarificación (22/10/2026).** Se resolvieron tres hallazgos graves: (C5) la fecha se lee solo como `AAAA-MM-DD` o con un `formato_fecha` explícito, sin inferir, y una fecha vacía o ilegible es un error (RF-2); (C1) en modo "invierno", `meses_frio` no puede cruzar el fin de año (RF-9); (C16 y C2) el parámetro `invierno` pasa a llamarse `campana` y enlaza la campaña `Y` con el período de etiqueta `Y`, con una advertencia `CAMPANA_NO_INDICADA` cuando no se indica (RF-22, RF-23, RF-28).
