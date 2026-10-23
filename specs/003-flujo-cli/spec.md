# Spec 003 — Flujo completo y línea de comandos

Estado: BORRADOR (pendiente de clarificación)

## Contexto y objetivo
Las specs 001 y 002 dejaron un núcleo que corrige por malla, clasifica ambientes, recomienda y calcula el estado de frío desde temperaturas diarias. Hoy cada pieza se llama por separado desde Python: leer el CSV, cruzar con la malla, generar el mapa, calcular el clima, elegir la campaña y llamar a `analizar()`. Esta spec une todo en un flujo que se corre desde una línea de comandos, sin escribir Python.

El flujo respeta el control de la spec 001: **primero se mira el mapa y después se analiza**. Por eso hay dos comandos: `mapa` genera el mapa de verificación y muestra la **huella** del lote; `analizar` exige esa huella para correr. La huella no es una contraseña: es la constancia de que quien analiza vio el mismo conjunto de plantas bajo malla que se dibujó.

Esta capa es fina: lee archivos, llama a las funciones existentes y escribe resultados. No contiene cálculo propio ni cambia el comportamiento del núcleo (constitución #6).

## Usuarios / actores
- **Investigador/a** que corre el análisis del lote y guarda los resultados.
- **Técnico/a de campo** que abre el mapa y lee la tabla de recomendaciones, sin programar.

## Historias de usuario
- **H1.** Como investigador/a, quiero correr el análisis desde la terminal con mis archivos (CSV de plantas, GeoJSON de la malla y CSV de clima), para no escribir código cada vez.
- **H2.** Como investigador/a, quiero ver el mapa y recibir la huella antes de analizar, para confirmar que la malla quedó donde corresponde.
- **H3.** Como investigador/a, quiero que el estado de frío salga del clima de la campaña elegida, y saber cuál se usó, para no escribirlo a mano.
- **H4.** Como investigador/a, quiero una carpeta con la tabla, el resumen y las advertencias, para guardar y compartir lo que se corrió y con qué parámetros.
- **H5.** Como investigador/a, quiero que un archivo mal formado o un parámetro equivocado dé un mensaje claro y no una traza de Python.

## Entradas

**Comandos.** `kiwitracking mapa` y `kiwitracking analizar` (también `python -m kiwitracking`).

**Comunes a los dos comandos**
- `--depurar`: muestra la traza completa de un error inesperado (RF-19).
- `--plantas`: CSV de plantas con `id`, `KVPI_mean`, `KVPI_std`, `X` e `Y` (longitud y latitud). Si trae `bajo_malla`, se puede omitir `--malla`.
- `--malla`: GeoJSON con la zona bajo malla (opcional si el CSV trae `bajo_malla`).
- `--crs-plantas`: sistema de coordenadas de `X` e `Y` (por ejemplo `EPSG:4326`). Obligatorio cuando se indica `--malla`.

**`mapa`**
- `--salida`: archivo HTML del mapa (por defecto, `mapa.html`).
- `--sin-fondo-satelital`: dibuja el mapa sin las teselas satelitales (no necesita internet).
- `--sobrescribir`: permite reemplazar un archivo existente.

**`analizar`**
- `--huella`: huella que mostró `mapa` (obligatoria).
- `--salida`: carpeta de resultados (por defecto, `resultados`).
- `--sobrescribir`: permite reemplazar resultados existentes.
- Parámetros de la spec 001, con sus mismos valores por defecto: `--correccion` (`auto`, `forzar` o `desactivar`), `--prueba-t` (`welch` o `student`), `--alfa`, `--min-plantas-grupo`, `--p-ambiente` (dos valores), `--p-estabilidad` y `--no-escalar-std`.
- Frío de la última campaña, con una de estas dos formas (o ninguna):
  - `--clima`: CSV con `date`, `Tmax` y `Tmin`; con `--campana` (año de inicio) y los parámetros de la spec 002 `--ventana-frio`, `--formato-fecha`, `--cobertura-minima` y `--max-hueco-dias` (entero o `ninguno`).
  - `--estado-frio`: `Deficiente`, `Adecuado` u `Óptimo`, escrito a mano.

El resto de los parámetros de la spec 002 (`tbase`, `umbral_frio`, `meses_frio` y los demás) quedan en sus valores por defecto: no se exponen en esta versión.

## Requisitos funcionales

**Comandos y ayuda**
- **RF-1.** El sistema DEBE ofrecer el programa `kiwitracking` con los subcomandos `mapa` y `analizar`. SI se ejecuta sin subcomando o con `--help`, ENTONCES DEBE mostrar una ayuda en español que liste los subcomandos y sus opciones. SI el subcomando no existe, ENTONCES DEBE terminar con un error de uso (RF-19).

**Lectura de las plantas y la malla**
- **RF-2.** El sistema DEBE leer el CSV de plantas con la lectura de la spec 001 (UTF-8, tolera el BOM de Excel; RF-3 y RF-4 de esa spec). SI el archivo no existe, ENTONCES DEBE terminar con un error que nombre el archivo.
- **RF-3.** CUANDO se indique `--malla`, el sistema DEBE leer el GeoJSON, exigir `--crs-plantas` y calcular `bajo_malla` con el cruce de la spec 001 (RF-17 a RF-19 de esa spec), incluidas sus advertencias. SI falta `--crs-plantas`, ENTONCES DEBE terminar con un error que lo pida.
- **RF-4.** CUANDO no se indique `--malla`, el sistema DEBE usar la columna `bajo_malla` del CSV. SI el CSV no la trae, ENTONCES DEBE terminar con un error que diga que hace falta `--malla` o esa columna.
- **RF-5.** CUANDO se indique `--malla` y el CSV ya traiga `bajo_malla`, el sistema DEBE usar el valor calculado con la malla y registrar una advertencia `BAJO_MALLA_REEMPLAZADO` con la cantidad de plantas cuyo valor cambió.

**Comando `mapa`**
- **RF-6.** El comando `mapa` DEBE generar el mapa de verificación de la spec 001 (RF-15) en el archivo indicado, y mostrar en pantalla la huella, la cantidad de plantas bajo malla y fuera de malla, y las advertencias. La huella DEBE imprimirse en una línea propia con el formato exacto `Huella: ` seguido de los 12 caracteres de la huella, sin otro texto en esa línea (RF-26). El mapa DEBE dibujarse con las plantas y el polígono convertidos a `EPSG:4326` (RF-23). SI el archivo ya existe y no se indicó `--sobrescribir`, ENTONCES DEBE terminar con un error sin tocarlo.
- **RF-7.** CUANDO se indique `--sin-fondo-satelital`, el mapa NO DEBE pedir teselas satelitales.
- **RF-26.** El único formato de pantalla que forma parte del contrato es la línea de la huella de RF-6 (y la de `analizar`, si la repite): NO DEBE cambiar sin cambiar esta spec. El resto del texto de pantalla es para personas y puede cambiar de redacción. Los datos para otros programas están en los archivos de resultados (RF-15 y RF-25).
- **RF-27.** `plantas.csv` DEBE llevar las columnas en este orden: `id`, `KVPI_mean`, `KVPI_corregido`, `KVPI_std`, `estabilidad`, `ambiente`, `recomendacion`, `bajo_malla`, y a continuación todas las demás columnas de entrada en su orden original (por ejemplo `X`, `Y`, `elev_m`). Las filas DEBEN salir en el orden de entrada. Si el CSV de entrada ya traía columnas de resultado (`KVPI_corregido`, `estabilidad`, `ambiente`, `recomendacion`), DEBEN reemplazarse por las calculadas. `bajo_malla` DEBE llevar el valor usado en el análisis (RF-3 a RF-5). El archivo DEBE ser el mismo aunque cambie el orden de las columnas del CSV de entrada.
- **RF-23.** Para dibujar el mapa, el sistema DEBE convertir a `EPSG:4326` las coordenadas de las plantas (desde el sistema de `--crs-plantas`) y el polígono (desde el sistema declarado en el GeoJSON). La conversión es solo para dibujar: NO DEBE cambiar `bajo_malla`, la huella ni los resultados. SI no se indica `--crs-plantas` (porque el CSV ya trae `bajo_malla`), ENTONCES DEBE suponer que las coordenadas ya están en longitud y latitud y comprobarlo con el control de la spec 001 (RF-15 de esa spec). SI un sistema de coordenadas no se reconoce, ENTONCES DEBE terminar con un error que lo nombre.

**Comando `analizar`**
- **RF-8.** El comando `analizar` DEBE exigir `--huella`. SI falta, ENTONCES DEBE terminar con un error de entrada (código 1, no el error de uso de la biblioteca de argumentos) que explique que hay que correr `mapa` primero y copiar la huella que muestra; por eso la opción no se declara obligatoria ante esa biblioteca, aunque la ayuda la marque como obligatoria. En la spec 001, una huella ausente o que no coincide no es un error: el análisis corre sin corrección y avisa (`FALTA_CONFIRMACION` y `HUELLA_NO_COINCIDE`, RF-8 y RF-9 de esa spec). La línea de comandos es más estricta: SI el análisis informa una de esas dos advertencias, ENTONCES `analizar` DEBE terminar con un error de entrada (código 1), sin escribir ningún archivo, en cualquier modo de corrección (incluido `--correccion forzar`). El mensaje DEBE decir que la huella no corresponde a estos datos, que el conjunto de plantas bajo malla es distinto del que mostró `mapa`, que se revisen los mismos `--plantas`, `--malla` y `--crs-plantas` en los dos comandos y que los archivos no hayan cambiado, y que se corra `mapa` de nuevo. El mensaje NO DEBE imprimir la huella correcta. El núcleo no cambia: la conversión de advertencia en error es solo de la línea de comandos.
- **RF-9.** El comando `analizar` DEBE pasar los parámetros indicados a `analizar()` y usar sus valores por defecto cuando no se indiquen. SI un valor no está permitido, ENTONCES DEBE terminar con el error de validación de la spec 001, que nombra los permitidos.
- **RF-10.** CUANDO se indique `--clima`, el sistema DEBE leerlo con la lectura de la spec 001, calcular el clima con los parámetros de la spec 002 y elegir el estado de frío de la campaña con `--campana` (o el más reciente clasificable si no se indica). El estado elegido DEBE alimentar el análisis.
- **RF-11.** CUANDO se indique `--estado-frio`, el sistema DEBE usarlo como estado de frío de la última campaña. SI se indican `--clima` y `--estado-frio` a la vez, ENTONCES DEBE terminar con un error que diga que son excluyentes.
- **RF-24.** SI se indica alguna de las opciones de clima (`--campana`, `--ventana-frio`, `--formato-fecha`, `--cobertura-minima` o `--max-hueco-dias`) sin `--clima`, ya sea sola o junto con `--estado-frio`, ENTONCES el sistema DEBE terminar con un error de entrada (código 1) que nombre la opción y diga que solo se usa con `--clima`. NO DEBE ignorarla en silencio.
- **RF-12.** SI no se indica ni `--clima` ni `--estado-frio`, ENTONCES el sistema DEBE correr el análisis sin ajuste por frío y mostrar la advertencia correspondiente de la spec 001 (RF-25 de esa spec).
- **RF-13.** SI con `--clima` ninguna ventana es clasificable, ENTONCES el sistema NO DEBE detenerse: DEBE correr sin ajuste por frío y registrar la advertencia `SIN_PERIODO_CLASIFICABLE` de la spec 002. En ese caso salen dos avisos, sin suprimir ninguno: `SIN_PERIODO_CLASIFICABLE` (la causa) y, después, `SIN_ESTADO_FRIO` de la spec 001 (la consecuencia: no se aplicó el ajuste). SI se indica `--campana` y ese período no existe o no es clasificable, ENTONCES DEBE terminar con el error de la spec 002 (RF-23 de esa spec).
- **RF-14.** Las advertencias DEBEN reunirse en este orden: las del cruce con la malla, las del clima, las de la elección de campaña y las del análisis.

**Salidas**
- **RF-15.** El comando `analizar` DEBE escribir en la carpeta de salida tres archivos: `plantas.csv` (la tabla por planta de la spec 001, con las columnas de RF-27), `resumen.json` y `advertencias.json`. El resumen DEBE incluir la huella, los valores del resumen de la spec 001, los parámetros usados y el estado de frío con su origen, con la estructura y las reglas de escritura de RF-25. `advertencias.json` DEBE traer, por cada advertencia, su código y su mensaje.
- **RF-16.** Los archivos DEBEN escribirse en UTF-8 sin BOM, con `
` como salto de línea en cualquier sistema operativo, y el CSV DEBE conservar los números completos, sin redondear (constitución #8). Dos corridas con los mismos archivos y parámetros DEBEN producir archivos de resultados idénticos byte a byte.
- **RF-17.** SI la carpeta de salida ya contiene alguno de esos tres archivos y no se indicó `--sobrescribir`, ENTONCES el sistema DEBE terminar con un error sin modificar nada.
- **RF-18.** El comando `analizar` DEBE mostrar en pantalla un resumen corto (cantidad de plantas, FC y si se corrigió, cantidad por recomendación, estado de frío usado y su origen) y las advertencias, y decir dónde quedaron los archivos.
- **RF-25.** `resumen.json` DEBE ser JSON estricto (UTF-8, sangría de 2 espacios, línea final, claves en el orden indicado) con esta estructura: `huella`; `resumen` (`fc`, `p_valor`, `n_bajo_malla`, `n_fuera_malla`, `correccion_aplicada`, `p33`, `p66`, `p75_estabilidad`, `escalar_std`, `prueba_t`); `parametros` (los usados, con `p_ambiente` como lista de dos números); y `estado_frio` (`origen` con el valor `clima`, `manual` o `ninguno`, `estado` y, cuando salió del clima, `periodo`, `horas`, `cobertura` y `hueco_maximo`). Los valores vacíos, `NaN` e infinitos DEBEN escribirse como `null`; los números de NumPy DEBEN escribirse como números comunes; los decimales DEBEN conservar todas sus cifras, sin redondear. El archivo DEBE poder leerse con un lector JSON estricto y devolver los mismos valores del resumen.

**Errores y códigos de salida**
- **RF-19.** El sistema DEBE terminar con código 0 cuando el comando se completa, con código 1 cuando hay un error de entrada (cualquier `ErrorDeEntrada` o archivo que no existe) y con código 2 cuando el uso es incorrecto (opción desconocida, falta una opción obligatoria). Los errores DEBEN mostrarse en español por la salida de errores, sin traza de Python, con el formato `Error: <mensaje>`. Con código 3, el sistema DEBE terminar ante cualquier error inesperado (una excepción que no es un error de entrada: un fallo del programa y no de los datos), mostrando por la salida de errores `Error inesperado: <tipo>: <mensaje>` y que parece un fallo del programa, no de los datos. CUANDO se indique `--depurar`, DEBE mostrar además la traza completa. Un error inesperado NO DEBE ocultarse.
- **RF-20.** El sistema NO DEBE modificar los archivos de entrada, y ante un error NO DEBE dejar archivos de salida a medio escribir.
- **RF-21.** Las rutas con espacios y con tildes DEBEN funcionar.
- **RF-22.** La salida por pantalla NO DEBE fallar por la codificación de la consola (en Windows, por ejemplo, al mostrar "Óptimo").

## Requisitos no funcionales
- La capa de comandos no contiene cálculo: llama a las funciones de las specs 001 y 002 (constitución #6). No cambia su comportamiento.
- Todo valor por defecto sale de las funciones existentes, para que haya una sola definición (constitución #7).
- La lectura y la escritura de archivos viven en la capa de entrada y salida, con UTF-8 (constitución #8). No hay rutas fijas (constitución #9).
- Las dependencias siguen siendo las del paquete: sin librerías nuevas para la línea de comandos (se usa la biblioteca estándar).

## Casos límite
- CSV de plantas con `bajo_malla` y sin `--malla`: se usa tal cual (RF-4).
- `--malla` con un CSV que ya trae `bajo_malla`: gana el cálculo con la malla y se avisa (RF-5).
- Lote sin malla (todas fuera de malla): el análisis corre sin corrección, como en la spec 001 (RF-10 de esa spec).
- Plantas o malla en un sistema distinto de `EPSG:4326` (por ejemplo, UTM): el mapa las convierte para dibujar (RF-23) y el cruce usa el sistema declarado (RF-3); se pueden mezclar sistemas distintos entre plantas y malla.
- CSV con `bajo_malla`, sin `--malla` y sin `--crs-plantas`, con coordenadas proyectadas: el control de rango de la spec 001 da error en `mapa`, que pide declarar `--crs-plantas`.
- `analizar` con una huella copiada con un espacio o en mayúsculas: se compara tal cual; no coincide y `analizar` da el error de RF-8.
- `--campana 2024` sin `--clima`: error (RF-24); el análisis no corre sin ajuste por frío creyendo que se aplicó.
- `--p-ambiente` con un solo valor o con valores fuera de rango: error de validación de la spec 001.
- `--clima` con una columna de temperatura con coma decimal: el error de la spec 002 (RF-3) con su causa probable.
- Carpeta de salida inexistente: se crea. Carpeta con otros archivos que no son los tres: se respetan y no se tocan.
- Dos corridas seguidas con los mismos archivos y parámetros: producen los mismos archivos de resultados.

## Fuera de alcance
- Interfaz gráfica o web.
- Empaquetar un ejecutable o publicar el paquete.
- Cambiar los cálculos del núcleo o el comportamiento de las specs 001 y 002.
- Leer otros formatos (Excel, shapefile, GeoPackage).
- Un archivo de configuración con los parámetros.
- Exponer en la línea de comandos todos los parámetros de la spec 002.
- Rellenar los datos faltantes del clima.

## Criterios de finalización
1. Todos los tests `RF-n` pasan, con avisos tratados como errores.
2. **Mapa:** sobre `datos_plantas_completos.csv` y `malla_zona.geojson` (`--crs-plantas EPSG:4326`), `mapa` informa 53 plantas bajo malla y 106 fuera, y una huella igual a la de `huella()` sobre ese lote.
3. **Flujo completo:** `mapa` y luego `analizar` con `--clima clima_diario.csv --campana 2024` dan 16 "Mantener" y 19 "Intervenir", con estado de frío "Óptimo" (período 2024) en el resumen. Sin `--campana`, el estado es "Adecuado" (período 2025) y `advertencias.json` trae `CAMPANA_NO_INDICADA`.
4. **Reproduce lo publicado:** con `--no-escalar-std` y `--estado-frio Deficiente`, `plantas.csv` tiene el mismo `KVPI_corregido`, `ambiente` y `recomendacion` que `datos_plantas_completos.csv` (0 "Mantener" y 19 "Intervenir").
5. **Control de la huella:** `analizar` con una huella incorrecta o ausente termina con código 1, incluso con `--correccion forzar`, sin escribir ningún archivo, y el mensaje no imprime la huella correcta.
6. Cada error de entrada conocido da un mensaje claro, sin traza, y código de salida 1.
7. **Mapa en otro sistema:** con las plantas y la malla del lote de referencia convertidas a otro sistema (por ejemplo, un sistema proyectado de Argentina) y declaradas con `--crs-plantas`, `mapa` da las mismas 53 plantas bajo malla y la misma huella, y dibuja los mismos puntos (diferencia menor que 1e-6 grados) y el mismo polígono que con el lote original.
8. Cada requisito tiene al menos un test asociado (fase de Validación).

## Dudas abiertas
- **[NECESITA ACLARACIÓN]** Hay que copiar la huella a mano de un comando al otro. Alternativa: que `mapa` guarde la huella en un archivo (por ejemplo, junto al HTML) y `analizar` pueda leerla con `--huella-desde`. Es más cómodo pero más fácil de saltearse la revisión del mapa.
- **[NECESITA ACLARACIÓN]** Los nombres de las columnas de coordenadas están fijos (`X` e `Y`). El núcleo admite otros nombres, pero la línea de comandos no los expone.
- **[NECESITA ACLARACIÓN]** `resumen.json` registra los parámetros usados, pero no la versión del paquete ni la fecha de la corrida: para reproducir una corrida alcanzaría con los parámetros, aunque conviene decidir si se agregan.
- **[NECESITA ACLARACIÓN]** Si `--sobrescribir` reemplaza solo los tres archivos o también limpia la carpeta: aquí solo los tres.

## Historial de cambios
- **Clarificación (22/10/2026).** Se resolvió C6: `plantas.csv` lleva un orden fijo de columnas conocidas y después las demás de entrada; las columnas de resultado que ya venían se reemplazan (RF-27).
- **Clarificación (22/10/2026).** Se resolvió C5: un error inesperado termina con código 3, con un mensaje corto y la traza solo con `--depurar` (RF-19).
- **Clarificación (22/10/2026).** Se resolvió C4: la falta de `--huella` es un error de entrada con código 1 y el mensaje de RF-8, igual que una huella incorrecta; la opción no es obligatoria para la biblioteca de argumentos (RF-8).
- **Clarificación (22/10/2026).** Se resolvió C2 y se corrigió un error de la spec: en la spec 001 la huella ausente o incorrecta es una advertencia (el análisis corre sin corrección), no un error. La línea de comandos es más estricta y la convierte en error de entrada, con un mensaje que explica la causa probable y no imprime la huella correcta (RF-8).
- **Clarificación (22/10/2026).** Se resolvió C12: la línea `Huella: <12 caracteres>` es el único formato de pantalla fijo (RF-6, RF-26); el resto es libre.
- **Clarificación (22/10/2026).** Se resolvió C11: sin ventana clasificable salen los dos avisos (`SIN_PERIODO_CLASIFICABLE` y después `SIN_ESTADO_FRIO`), sin filtrar ninguno (RF-13).
- **Clarificación (22/10/2026).** Se resolvió C10: los archivos de resultados usan `
` como salto de línea en todos los sistemas, y dos corridas iguales dan archivos idénticos byte a byte (RF-16).
- **Clarificación (22/10/2026).** Se resolvió C7: `resumen.json` es JSON estricto con estructura fija (RF-25); vacíos, `NaN` e infinitos como `null`.
- **Clarificación (22/10/2026).** Se resolvió C3: una opción de clima sin `--clima` es un error, no se ignora (RF-24).
- **Clarificación (22/10/2026).** Se resolvió el hallazgo grave C1: el mapa convierte plantas y polígono a `EPSG:4326` solo para dibujar (RF-23), lo que además deja de limitar el mapa a coordenadas en longitud y latitud.
- **Borrador (22/10/2026).** Alcance acordado en la entrevista: flujo completo con dos comandos (`mapa` y `analizar`), plantas desde CSV con coordenadas más malla GeoJSON, huella en dos pasos, clima opcional con `--campana` y salidas en una carpeta con tabla, resumen y advertencias.
