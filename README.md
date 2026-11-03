# KiwiTracking

Programa de línea de comandos que, a partir de la serie de KVPI (un índice que se calcula con imágenes Sentinel-2 a partir de NDVI, NDRE, NDMI y EVI) de un lote de kiwi, corrige el efecto de la malla de protección, clasifica los ambientes del lote y recomienda el manejo de cada planta. Es el software de la tesis *Análisis de variabilidad productiva para kiwi integrando teledetección, topografía y machine learning*.

## Qué hace

Tiene tres comandos, que se usan en este orden:

- **`kvpi`** junta la serie de KVPI por planta y campaña con las coordenadas de las plantas y calcula, por planta, el promedio, el desvío y la cantidad de campañas con dato.
- **`mapa`** dibuja las plantas y la zona bajo malla en un mapa HTML y muestra una huella, que identifica el conjunto de plantas bajo malla: hay que revisar el mapa antes de seguir.
- **`analizar`** corrige el KVPI por el efecto de la malla, clasifica los ambientes (Alto Potencial, Transicional y Limitante) y recomienda "Mantener", "Observar" o "Intervenir" para cada planta. Con el clima diario, además, ajusta la recomendación según las horas de frío del invierno.

## Qué no hace

- **No hace el paso de Google Earth Engine** (descargar imágenes y calcular el KVPI por campaña): parte de la serie ya exportada.
- **Solo se probó con el lote de referencia de la tesis.** Con otros lotes, otros cultivos u otras mallas no está verificado.
- El clima de referencia trae días interpolados (no mediciones); el programa lo avisa. Los detalles están en la guía.

## Instalación

Necesitás **Python 3.14**, la única versión con la que se probó el programa, y **Windows 11**, el único sistema en el que se probó. Con el archivo del paquete:

```bash
pip install kiwitracking-1.2.0-py3-none-any.whl
```

Para trabajar con el código, desde la carpeta del repositorio: `pip install -e ".[dev]"`. Para comprobar la instalación:

```bash
kiwitracking --version
```

## Ejemplo mínimo

Con una serie `serie.csv`, un muestreo `muestreo.csv`, una malla `malla.geojson` y un clima `clima_diario.csv` (los formatos están en la guía), en la carpeta donde estén:

<!-- prueba: ejemplo-minimo -->
```bash
kiwitracking kvpi --serie serie.csv --muestreo muestreo.csv --salida plantas_kvpi.csv
kiwitracking mapa --plantas plantas_kvpi.csv --malla malla.geojson --crs-plantas EPSG:4326 --salida mapa.html --sin-fondo-satelital
kiwitracking analizar --plantas plantas_kvpi.csv --malla malla.geojson --crs-plantas EPSG:4326 --huella HUELLA --clima clima_diario.csv --campana 2024 --salida resultados
```

Reemplazá `HUELLA` por la huella de 12 caracteres que mostró `mapa`. Con los datos del lote de referencia (159 plantas, 53 bajo malla) el resultado es: `kvpi` escribe `plantas_kvpi.csv` con las 159 plantas, `mapa` escribe `mapa.html` y muestra la huella, y `analizar` escribe `plantas.csv`, `resumen.json` y `advertencias.json` en `resultados`, con estado de frío "Óptimo" para la campaña 2024.

## Guía completa

Todas las opciones, los formatos de los archivos, las advertencias, los códigos de salida, cómo reproducir los resultados de la tesis y los límites del programa están en la [guía de uso](docs/uso.md).

## Cómo citar

Si usás KiwiTracking en tu investigación, citá la tesis asociada e indicá la versión que usaste (1.2.0). La versión 1.2.0 todavía no tiene DOI propio: el DOI que figura en [CITATION.cff](CITATION.cff) es el del proyecto en Zenodo. La referencia completa está en `CITATION.cff`.

## Licencia

[MIT](LICENSE). Copyright (c) 2026 Darío Nicolás Sánchez Leguizamón.
