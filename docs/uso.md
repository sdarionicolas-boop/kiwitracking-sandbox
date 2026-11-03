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
