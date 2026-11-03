# Guía de uso de KiwiTracking

Esta guía explica cómo instalar `kiwitracking` y cómo usar sus tres comandos para pasar de la serie de KVPI que exporta Google Earth Engine a las recomendaciones de manejo de un lote de kiwi. Está escrita para quien sabe abrir una terminal; todo lo que afirma está respaldado por un test o por un dato del repositorio.

## 1. Requisitos e instalación

**Qué necesitás.**
- **Python 3.14.** Es la única versión con la que se probó el programa.
- **Windows 11.** Es el único sistema en el que se probó; en otros puede andar, pero no está verificado.
- Las bibliotecas que usa el programa (`pandas`, `numpy`, `scipy`, `shapely`, `pyproj` y `folium`) se instalan solas con `pip`.

**Instalación desde el archivo del paquete.** Si tenés el archivo `kiwitracking-1.2.0-py3-none-any.whl` (se genera como se explica en la sección 8):

```bash
pip install kiwitracking-1.2.0-py3-none-any.whl
```

**Instalación para trabajar con el código.** Desde la carpeta del repositorio, con las herramientas de desarrollo (`pytest`, `build`):

```bash
pip install -e ".[dev]"
```

**Comprobación.** Con cualquiera de las dos instalaciones, este comando debe mostrar la versión (`kiwitracking 1.2.0`):

```bash
kiwitracking --version
```

Si el comando `kiwitracking` no se encuentra, probá con `python -m kiwitracking --version`: es lo mismo.

## 2. Recorrido completo

El recorrido tiene tres pasos, uno por comando:

1. **`kvpi`** junta la serie de KVPI por planta y campaña con las coordenadas de las plantas y escribe un CSV por planta (`plantas_kvpi.csv`).
2. **`mapa`** dibuja las plantas y la zona bajo malla en un mapa HTML y muestra una **huella** de 12 caracteres, que identifica el conjunto de plantas bajo malla. Hay que mirar el mapa y confirmar que la malla está donde corresponde.
3. **`analizar`** corrige el KVPI por el efecto de la malla, clasifica los ambientes y recomienda "Mantener", "Observar" o "Intervenir". Necesita la huella que mostró `mapa`: si cambia el conjunto de plantas bajo malla, la huella cambia y `analizar` se niega a seguir (código de salida 1).

Los ejemplos van en una sola línea y con barras comunes (`/`) en las rutas, así valen igual en PowerShell, `cmd` y `bash`. Los nombres de archivo son de ejemplo. En `analizar`, `HUELLA` hay que reemplazarlo por la huella que mostró `mapa`.

### `kvpi`

Agrega la serie de KVPI por planta (promedio, desvío muestral, coeficiente de variación y cantidad de campañas con dato) y la une con el muestreo. Escribe el archivo que después usan `mapa` y `analizar` como `--plantas`. Muestra en pantalla las campañas encontradas con su cobertura, cuántas plantas tienen cada cantidad de campañas y las advertencias.

```bash
kiwitracking kvpi --serie serie.csv --muestreo muestreo.csv --salida plantas_kvpi.csv
```

Opciones:

- `--serie` (obligatoria): CSV de la serie, con una fila por planta y campaña (columnas `id`, `campaña` y `KVPI`).
- `--muestreo` (obligatoria): CSV del muestreo, con una fila por planta (columnas `id`, `X` e `Y`).
- `--salida`: archivo CSV de resultados. Si ya existe, hay que agregar `--sobrescribir`. (por defecto: plantas_kvpi.csv)
- `--min-campanas`: campañas con dato mínimas para calcular el desvío de una planta; un entero de 2 en adelante. Con menos, el desvío queda vacío pero el promedio se conserva. (por defecto: 2)
- `--campanas`: etiquetas de campaña esperadas, separadas por comas. Si falta o sobra alguna en la serie, el comando se detiene con un error que las nombra.
- `--cobertura-minima-campana`: proporción mínima de plantas con dato que debe tener cada campaña, entre 0 y 1; por debajo sale una advertencia. (por defecto: 0.5)
- `--sobrescribir`: permite reemplazar el archivo de salida si ya existe.
- `--depurar`: ante un error inesperado muestra la traza completa.

### `mapa`

Dibuja el mapa de verificación y muestra la huella del lote, la cantidad de plantas bajo malla y fuera de ella. El mapa pide internet para el fondo satelital; con `--sin-fondo-satelital` se dibuja sin las teselas y no usa la red.

```bash
kiwitracking mapa --plantas plantas_kvpi.csv --malla malla.geojson --crs-plantas EPSG:4326 --salida mapa.html --sin-fondo-satelital
```

Opciones:

- `--plantas` (obligatoria): CSV por planta, con `id`, `KVPI_mean`, `KVPI_std`, `X` e `Y` (el que escribió `kvpi`).
- `--malla`: GeoJSON con el polígono de la zona bajo malla. Es opcional si el CSV de plantas ya trae la columna `bajo_malla`.
- `--crs-plantas`: sistema de coordenadas de `X` e `Y`, por ejemplo `EPSG:4326`; es obligatorio si se usa `--malla`.
- `--depurar`: ante un error inesperado muestra la traza completa.
- `--salida`: archivo HTML del mapa. Si ya existe, hay que agregar `--sobrescribir`. (por defecto: mapa.html)
- `--sin-fondo-satelital`: dibuja el mapa sin las teselas satelitales.
- `--sobrescribir`: permite reemplazar un archivo existente.

### `analizar`

Corrige el KVPI por malla, calcula la estabilidad de cada planta, clasifica los ambientes y recomienda. Si se le da el clima diario, calcula las horas de frío del invierno de una campaña y ajusta la recomendación según el estado de frío. Escribe en la carpeta de resultados `plantas.csv`, `resumen.json` y `advertencias.json`, y muestra un resumen en pantalla.

```bash
kiwitracking analizar --plantas plantas_kvpi.csv --malla malla.geojson --crs-plantas EPSG:4326 --huella HUELLA --clima clima_diario.csv --campana 2024 --salida resultados
```

Opciones:

- `--plantas` (obligatoria): CSV por planta, el mismo que se le dio a `mapa`.
- `--malla`: GeoJSON con la zona bajo malla; el mismo que se le dio a `mapa`.
- `--crs-plantas`: sistema de coordenadas de `X` e `Y`; es obligatorio si se usa `--malla`.
- `--depurar`: ante un error inesperado muestra la traza completa.
- `--huella` (obligatoria): la huella que mostró `mapa`. Si no coincide con el conjunto de plantas bajo malla, el comando termina con un error.
- `--salida`: carpeta de resultados; se crea si no existe. Si ya tiene resultados, hay que agregar `--sobrescribir`. (por defecto: resultados)
- `--sobrescribir`: permite reemplazar resultados existentes.
- `--correccion`: modo de la corrección por malla: `auto` corrige si la diferencia entre plantas bajo malla y fuera de ella es significativa, `forzar` corrige igual (con una advertencia) y `desactivar` no corrige. (por defecto: auto)
- `--prueba-t`: prueba t con la que se evalúa esa diferencia: `welch` (no supone varianzas iguales) o `student` (las supone). (por defecto: welch)
- `--alfa`: nivel de significancia de la prueba t. (por defecto: 0.05)
- `--min-plantas-grupo`: plantas mínimas que tiene que haber bajo malla y fuera de ella para corregir. (por defecto: 2)
- `--p-ambiente`: dos percentiles, el bajo y el alto, que separan los ambientes; se escriben así: `--p-ambiente 33 66`. (por defecto: 33 66)
- `--p-estabilidad`: percentil de estabilidad que se usa para recomendar "Mantener". (por defecto: 75)
- `--no-escalar-std`: no escala el desvío con el factor de corrección; sin esta opción se escala.
- `--clima`: CSV de clima diario con las columnas `date`, `Tmax` y `Tmin`, y opcionalmente `origen`. Con él se calcula el estado de frío; no se puede usar junto con `--estado-frio`.
- `--campana`: año de inicio de la campaña, por ejemplo `2024`; el programa usa el invierno de ese año. Sin ella usa el más reciente que se pueda clasificar y lo avisa. Solo con `--clima`.
- `--ventana-frio`: ventana de las horas de frío: `invierno` (de mayo a agosto) o `temporada`. Solo con `--clima`. (por defecto: invierno)
- `--formato-fecha`: formato de las fechas del clima si no son AAAA-MM-DD, por ejemplo `%d/%m/%Y`. Solo con `--clima`.
- `--cobertura-minima`: proporción mínima de días con datos para que un período se pueda clasificar, entre 0 y 1. Solo con `--clima`. (por defecto: 0.9)
- `--max-hueco-dias`: máximo de días seguidos sin datos que tolera un período, o `ninguno` para no limitarlo. Solo con `--clima`. (por defecto: 7)
- `--origenes-estimados`: etiquetas de la columna `origen` del clima que cuentan como días estimados, separadas por comas; sirve para el aviso de días estimados. Solo con `--clima`. (por defecto: interpolado)
- `--estado-frio`: estado de frío escrito a mano en lugar de calcularlo: `Deficiente`, `Adecuado` u `Óptimo` (sin distinguir mayúsculas ni tildes). No se puede usar junto con `--clima`.

Sin `--clima` ni `--estado-frio`, `analizar` corre igual pero no aplica el ajuste por frío y lo avisa.

### Opciones generales

Valen para el programa completo.

- `--help`: muestra la ayuda en la terminal y termina; también sirve con cada comando (por ejemplo, `kiwitracking mapa --help`).
- `--version`: muestra la versión instalada y termina.

## 3. Formatos de los archivos de entrada

**Todos los CSV** van en UTF-8 (se acepta el BOM que agrega Excel al guardar como UTF-8), con los valores separados por comas, **punto decimal** (`0.45`, no `0,45`) y los nombres de las columnas en la primera fila. Los nombres de las columnas distinguen mayúsculas (`KVPI_mean`, `Tmax`). Una celda vacía es un dato que falta.

### Serie

La serie de KVPI que exporta Earth Engine: una fila por planta y campaña. Es la entrada de `kvpi`.

- **Obligatorias:** `id`, `campaña` (o `campana`, pero no las dos a la vez) y `KVPI`.
- **Las demás columnas** de la exportación (`.geo`, `row`, `col`, `system:index`…) se ignoran.
- Una celda de `KVPI` vacía es una campaña sin dato (no es un error). Un texto que no es un número (por ejemplo `n/d`) sí es un error, y con decimales escritos con coma el mensaje lo señala como causa probable.
- La etiqueta de campaña (`2019_2020`) es un texto: no se interpreta ni se ordena, solo se le quitan los espacios del principio y del final.
- Una planta con la misma campaña repetida y el mismo valor se cuenta una sola vez (con una advertencia); con valores distintos es un error, porque ningún promedio lo corrige.

### Muestreo

Las coordenadas de las plantas: una fila por planta. Es la otra entrada de `kvpi`.

- **Obligatorias:** `id`, `X` e `Y`.
- **Las demás columnas** (por ejemplo `row_index`, `col_index`) se conservan y pasan al resultado.
- Una planta con `X` o `Y` vacías queda fuera, con una advertencia. Un `id` repetido con todos los valores iguales se cuenta una vez; con valores distintos es un error.

### Plantas

El CSV por planta que usan `mapa` y `analizar`. Normalmente es el que escribió `kvpi` (`plantas_kvpi.csv`), pero puede ser cualquier CSV con estas columnas.

- **Obligatorias:** `id`, `KVPI_mean` y `KVPI_std`.
- **Según el comando:** `X` e `Y` (las necesita `mapa`, y también cualquier comando que reciba `--malla`) y `bajo_malla` (vale `1` bajo malla y `0` fuera; hace falta si no se usa `--malla`, porque con `--malla` se calcula).
- Una planta con `KVPI_mean` vacío se excluye del análisis (con una advertencia); con `KVPI_std` vacío entra, pero sin estabilidad y con la recomendación "Observar".
- Las demás columnas (elevación, pendiente…) se conservan al final de `plantas.csv`.

### Malla

La zona bajo malla de protección, como un archivo GeoJSON.

- **Contenido:** un `Polygon` o un `MultiPolygon`, suelto o dentro de un `Feature` o de un `FeatureCollection`; si hay varios polígonos se juntan, y las geometrías que no son polígonos se ignoran. Sin ningún polígono es un error.
- **Sistema de coordenadas:** el que declara el miembro `crs` del archivo; si no lo trae, `EPSG:4326` (longitud y latitud), como indica el estándar GeoJSON. El de las plantas se declara con `--crs-plantas`; si es distinto, el programa convierte para comparar.

### Clima

El clima diario de la estación. Es opcional para `analizar` (con `--clima`).

- **Obligatorias:** `date`, `Tmax` y `Tmin`.
- **Opcionales:** `origen`.
- **La columna `origen`** es un texto libre que dice de dónde sale cada día, por ejemplo `INTA_verificado` o `interpolado`. Con ella el programa avisa cuántos días del período usado son estimados; sin ella no hay aviso.
- **Fechas:** `AAAA-MM-DD`; con otro formato hay que indicarlo con `--formato-fecha`.
- **Temperaturas:** en grados Celsius. El programa rechaza valores fuera de -60 a 60 y días con `Tmax` menor que `Tmin`. Un día con una temperatura vacía cuenta como día sin datos.
- Una fecha repetida con las mismas temperaturas se cuenta una vez (con una advertencia); con temperaturas distintas es un error.

## 4. Archivos de salida

Todos los archivos que escribe el programa van en **UTF-8 sin BOM**, con saltos de línea `\n`, los números con todos los decimales (sin redondear) y **celdas vacías** donde no hay valor. Ningún comando modifica sus archivos de entrada. Si `kvpi` falla al escribir, no deja un archivo a medio escribir (escribe primero un archivo temporal y lo mueve al destino al terminar); si falla `analizar`, borra lo que ya había escrito en esa corrida, salvo con `--sobrescribir`, donde los archivos de una corrida anterior que ya se reemplazaron no se recuperan.

### `plantas_kvpi.csv`

Lo escribe `kvpi`. Una fila por planta, en el orden del muestreo.

- `id`: identificador de la planta.
- `KVPI_mean`: promedio del KVPI de las campañas con dato.
- `KVPI_std`: desvío estándar muestral (divisor n−1) de esas campañas; vacío si la planta tiene menos de `--min-campanas`.
- `KVPI_cv`: coeficiente de variación, `KVPI_std / KVPI_mean`; vacío si el desvío está vacío o el promedio es 0.
- `n_campanas`: cantidad de campañas con dato.
- Después, las demás columnas del muestreo (`X`, `Y`…), en su orden.

### `plantas.csv`

Lo escribe `analizar` en la carpeta de resultados. Una fila por planta analizada, en el orden de entrada.

- `id`: identificador de la planta.
- `KVPI_mean`: el KVPI de entrada.
- `KVPI_corregido`: el KVPI de las plantas bajo malla multiplicado por el factor de corrección, si se corrigió; si no, igual a `KVPI_mean`.
- `KVPI_std`: el desvío de entrada.
- `estabilidad`: `KVPI_corregido / KVPI_std` (con `--no-escalar-std`) o `KVPI_mean / KVPI_std` (por defecto); vacía si `KVPI_std` es 0 o está vacío.
- `ambiente`: `Alto Potencial` (KVPI corregido en el percentil alto o por encima), `Limitante` (por debajo del percentil bajo) o `Transicional` (el resto), según `--p-ambiente`.
- `recomendacion`: `Mantener` (estable y de alto potencial), `Intervenir` (estable y limitante) u `Observar` (el resto, y las que no tienen estabilidad). Con estado de frío "Deficiente", ninguna planta queda en `Mantener`.
- `bajo_malla`: `1` o `0`.
- Después, las demás columnas de entrada en su orden (`KVPI_cv`, `n_campanas`, `X`, `Y`…).

### `resumen.json`

Lo escribe `analizar`. Un objeto JSON con cuatro claves; los valores que no se pudieron calcular valen `null`.

- `huella`: la huella de 12 caracteres con la que se corrió.
- `resumen`: el resultado global.
  - `fc`: factor de corrección (media fuera de malla sobre media bajo malla).
  - `p_valor`: valor p de la prueba t que compara los dos grupos.
  - `n_bajo_malla` y `n_fuera_malla`: cantidad de plantas de cada grupo.
  - `correccion_aplicada`: `true` si se corrigió el KVPI.
  - `p33` y `p66`: los umbrales de KVPI corregido que separan los ambientes (los percentiles de `--p-ambiente`).
  - `p75_estabilidad`: el umbral de estabilidad para `Mantener` e `Intervenir` (el percentil de `--p-estabilidad`).
  - `escalar_std`: `true` si el desvío se escaló con el factor de corrección.
  - `prueba_t`: la prueba usada, `welch` o `student`.
- `parametros`: los valores con los que se corrió, para poder repetir la corrida.
  - `correccion`, `alfa`, `min_plantas_grupo`, `p_ambiente`, `p_estabilidad`, `escalar_std` y `prueba_t`: los de las opciones del mismo nombre.
  - `clima`: solo con `--clima`; trae `ventana_frio`, `formato_fecha`, `cobertura_minima`, `max_hueco_dias`, `campana` y `origenes_estimados`.
- `estado_frio`: el estado de frío usado.
  - `origen`: `clima`, `manual` o `ninguno`.
  - `estado`: `Deficiente`, `Adecuado` u `Óptimo` (`null` si no hay).
  - Solo con origen `clima`: `periodo` (el año del invierno; con `--ventana-frio temporada`, el año en que empieza la temporada), `horas` (horas de frío), `cobertura` (proporción de días con datos), `hueco_maximo` (la mayor racha de días sin datos), `dias_estimados` (días del período que figuran como estimados) y `proporcion_estimada` (esa cantidad sobre los días con datos). Los dos últimos valen `null` si el clima no trae la columna `origen`.

### `advertencias.json`

Lo escribe `analizar`. Una lista de objetos, en el orden en que se produjeron, cada uno con dos claves: `codigo` (el nombre estable de la advertencia, que se explica en la sección 5) y `mensaje` (el texto para personas). Si no hubo ninguna advertencia, la lista está vacía.
