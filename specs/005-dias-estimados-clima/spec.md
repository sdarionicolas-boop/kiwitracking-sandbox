# Spec 005 — Aviso de días estimados en el clima

Estado: BORRADOR (pendiente de clarificación)

## Contexto y objetivo
El clima de referencia (`tests/golden/clima_diario.csv`) trae una columna `origen` que dice de dónde sale cada día: 2.546 días son mediciones de la estación de INTA (`INTA_verificado`) y 58 son valores **interpolados**, no mediciones (INTA los tiene vacíos y el hueco es definitivo; ver `AGENTS.md`). El programa hoy **ignora** esa columna: las horas de frío y el estado de la última campaña se calculan igual con unos días que con otros, y nada en la pantalla, en `resumen.json` ni en las advertencias lo dice.

Eso importa. El invierno 2024, el que decide el estado de frío "Óptimo" del lote de referencia, tiene 26 de sus 123 días interpolados (21 %); el de 2023 tiene 4 y el de 2025 tiene 8. Sin los interpolados, 2024 y 2025 ni siquiera serían clasificables. Quien lea "Óptimo (1.128,8 h)" no tiene forma de saber que una quinta parte del dato no es una medición.

Esta spec hace **visible** ese hecho sin cambiar ningún cálculo: si el período que decide el estado de frío tiene días estimados, el programa lo avisa con cuántos son y qué proporción del período representan, y lo deja registrado en `resumen.json`. No excluye los días, no los corrige y no cambia el estado ni las recomendaciones.

Amplía el RF-8 de la spec 002 (las columnas extra se ignoraban: `origen` deja de ser una columna extra) y el RF-25 de la spec 003 (estructura de `resumen.json`).

## Usuarios / actores
- **Investigador/a** que corre `analizar --clima` y necesita saber si el estado de frío descansa en días que no son mediciones.
- **Técnico/a de campo** que lee la pantalla y las advertencias y no debería tener que abrir el archivo del clima para enterarse.

## Historias de usuario
- **H1.** Como investigador/a, quiero que `analizar` me avise cuántos días del período usado son estimados, para no leer el estado de frío como más firme de lo que es.
- **H2.** Como investigador/a, quiero que `resumen.json` registre ese recuento, para que quede escrito junto al resultado.
- **H3.** Como investigador/a, quiero poder decir qué valores de `origen` cuentan como estimados, para usar mi propio archivo de clima con otras etiquetas.
- **H4.** Como usuario/a de un clima sin columna `origen`, quiero que todo siga funcionando como antes.

## Entradas
**Clima** (CSV): además de `date`, `Tmax` y `Tmin`, una columna **opcional** `origen` con texto libre (`INTA_verificado`, `interpolado`…). Una celda vacía es un día sin etiqueta: no cuenta como estimado.

**Parámetro nuevo:** `origenes_estimados`, la lista de etiquetas de `origen` que cuentan como día estimado (por defecto, `("interpolado",)`). Se compara sin espacios al inicio ni al final y sin distinguir mayúsculas.

**Línea de comandos:** `kiwitracking analizar --clima clima.csv [--origenes-estimados interpolado,estimado]`; la opción solo se usa con `--clima`, como las demás opciones de clima.

**Núcleo:** `ParametrosClima(origenes_estimados=("interpolado",))`. `calcular_clima` llena `ResultadoClima.estimados`; `estado_frio_de_campana` copia el recuento del período elegido a `EstadoCampana.dias_estimados` y `EstadoCampana.proporcion_estimada`; `elegir_estado_de_frio` los pasa a `EstadoDeFrio`.

## Requisitos funcionales

**Recuento por período**
- **RF-1.** SI el clima trae la columna `origen`, ENTONCES el sistema DEBE calcular, para cada ventana de frío, `dias_estimados` (los días disponibles de la ventana, con las dos temperaturas, cuyo `origen` está en `origenes_estimados`) y `proporcion_estimada` (`dias_estimados` sobre los días disponibles de la ventana; vacía si no hay días disponibles). El recuento DEBE guardarse en un campo nuevo `estimados` de `ResultadoClima`, con una fila por ventana (`periodo`, `dias_estimados`, `proporcion_estimada`), sin modificar la tabla `frio` ni `COLUMNAS_FRIO`.
- **RF-2.** SI el clima NO trae la columna `origen`, ENTONCES `estimados` DEBE quedar sin filas, `dias_estimados` y `proporcion_estimada` del estado elegido DEBEN quedar vacíos (no se sabe) y NO DEBE salir ningún aviso de días estimados. Todo lo demás funciona como antes.
- **RF-3.** Un día sin temperaturas (que no aporta al cálculo) NO DEBE contarse como estimado aunque tenga la etiqueta.
- **RF-4.** SI una fecha aparece repetida, ENTONCES el día DEBE contarse con la etiqueta de `origen` de su primera aparición, como el resto de las columnas (regla de la spec 002: se conserva la primera fila). Las etiquetas de las copias descartadas no se miran.
- **RF-5.** El recuento DEBE ser independiente del orden de las filas y de las columnas extra.

**Aviso**
- **RF-6.** SI el período que decide el estado de frío (el de la campaña indicada o el más reciente clasificable) tiene `dias_estimados` mayor que 0, ENTONCES el sistema DEBE registrar una advertencia `DIAS_ESTIMADOS` que nombre el período, diga cuántos días son estimados, de cuántos disponibles y qué porcentaje, y aclare que no son mediciones. Con 0 días estimados, o sin columna `origen`, no hay advertencia.
- **RF-7.** La advertencia `DIAS_ESTIMADOS` DEBE salir después de las demás advertencias de la elección de campaña (`CAMPANA_NO_INDICADA`, `COBERTURA_PARCIAL`).
- **RF-8.** El aviso NO DEBE cambiar el estado de frío, las horas, la clasificación, ni ningún resultado de `analizar`: es solo información.

**Parámetros**
- **RF-9.** `origenes_estimados` DEBE ser una lista (o tupla) no vacía de textos no vacíos. SI no lo es, ENTONCES el sistema DEBE detenerse con un error que nombre los valores permitidos.
- **RF-10.** SI se indica `--origenes-estimados` sin `--clima`, ENTONCES el comando DEBE terminar con el error de las demás opciones de clima (RF-24 de la spec 003). La opción recibe los valores separados por comas, sin espacios al inicio ni al final; un valor vacío da un error.

**Resumen**
- **RF-11.** `resumen.json` DEBE incluir en `estado_frio`, cuando el origen es `clima`, las claves `dias_estimados` y `proporcion_estimada` del período usado, a continuación de `hueco_maximo`; vacías (`null`) si el clima no trae `origen`. Con estado manual o sin estado no se agregan.

## Requisitos no funcionales
- No se agregan dependencias (constitución #1).
- El núcleo no lee ni escribe archivos (constitución #6, #9); el valor por defecto de `origenes_estimados` vive en `ParametrosClima` (constitución #7).
- Un clima sin la columna `origen` produce exactamente los mismos resultados que antes de esta spec: la tabla `frio` y `COLUMNAS_FRIO` no cambian y los 1.230 tests actuales siguen pasando sin modificarse.

## Casos límite
- Todos los días de la ventana son estimados: `dias_estimados` igual a los disponibles, proporción 100 %, aviso.
- Ventana clasificable con cobertura menor que 1 (por ejemplo, 119 de 123 días): el recuento sale igual y la proporción es sobre los días disponibles (119), no sobre los esperados (123).
- `origen` con valores que no están en `origenes_estimados` (por ejemplo `INTA_verificado`, `medido`, un texto cualquiera): no cuentan.
- `origen` numérico (por ejemplo `0` y `1`): se lee como texto; no coincide con la lista por defecto.
- Sin campaña indicada y con la ventana más reciente clasificable: el recuento es el de esa ventana, y el aviso nombra ese período.
- Un estado de frío escrito a mano (`--estado-frio`): no hay clima, no hay recuento ni aviso.

## Fuera de alcance
- Excluir los días estimados del cálculo, o tratarlos como días sin dato: se decidió solo avisar.
- Avisar sobre otras ventanas distintas de la que decide el estado, o sobre el GDD (el análisis de la spec 001 no lo usa).
- Calcular la interpolación o completar huecos del clima.
- Cambiar las etiquetas del archivo de referencia o modificar `clima_diario.csv`.
- Un umbral de proporción por debajo del cual no se avisa: se avisa siempre que haya al menos un día.

## Criterios de finalización
1. Todos los tests `RF-n` pasan, con avisos tratados como errores.
2. **Clima sintético:** con un clima armado a mano, `dias_estimados` y `proporcion_estimada` por ventana coinciden con lo contado a mano, incluidos los casos límite (todos estimados, ninguno, fechas repetidas, días sin temperaturas).
3. **Clima real:** con `clima_diario.csv`, el invierno 2024 da 26 días estimados de 123 (21,1 %), el 2023 da 4 de 123 y el 2025 da 8 de 119; `analizar --clima --campana 2024` trae la advertencia `DIAS_ESTIMADOS` con esas cifras, y `resumen.json` registra `dias_estimados` 26.
4. **Nada cambia:** con y sin la columna `origen`, `analizar` da las mismas recomendaciones (16 "Mantener" y 19 "Intervenir"), el mismo estado "Óptimo" y las mismas horas (1.128,8 h) en 2024.
5. **Compatibilidad:** con un clima sin columna `origen`, `resumen.json` trae `null` en los dos campos y no sale ninguna advertencia nueva.
6. Cada requisito tiene al menos un test asociado (fase de Validación).

## Dudas abiertas
- **[NECESITA ACLARACIÓN]** Sin la columna `origen` no hay aviso: el programa no puede saber si hay días estimados. Un clima sin columna y con `--origenes-estimados` indicado se acepta sin avisar que no hay con qué comparar.
- **[NECESITA ACLARACIÓN]** La proporción se calcula sobre los días **disponibles** de la ventana, no sobre los esperados. Con una ventana incompleta (cobertura menor que 1) las dos cifras difieren.
- **[NECESITA ACLARACIÓN]** El GDD por temporada también usa días interpolados y no se avisa; hoy no alimenta ninguna recomendación.
- **[NECESITA ACLARACIÓN]** Condiciones de uso de los datos de INTA (ver `AGENTS.md`): siguen sin verificarse antes de abrir el repositorio.

## Historial de cambios
- **Clarificación (02/11/2026).** Se resolvió C1: con fechas repetidas se usa el `origen` de la primera aparición, la regla de la spec 002; se quitó el criterio conservador (RF-4).
- **Clarificación (02/11/2026).** Se resolvió C2: el recuento por ventana va en un campo nuevo `ResultadoClima.estimados`, sin tocar la tabla `frio` ni `COLUMNAS_FRIO` (RF-1, RF-2 y requisitos no funcionales).
- **Borrador (02/11/2026).** Alcance acordado en la entrevista: solo avisar (sin excluir los días), la columna `origen` con el valor `interpolado` como criterio, configurable, y aviso siempre que haya al menos un día estimado en el período que decide el estado de frío.
