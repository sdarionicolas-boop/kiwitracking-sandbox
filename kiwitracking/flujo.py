"""Flujo de la línea de comandos sin consola (spec 003): une las piezas de las specs 001 y 002.

No importa `argparse` ni imprime: recibe valores y devuelve datos, para probarse sin consola. No calcula
nada propio: lee archivos y llama a las funciones que ya existen.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from shapely.geometry.base import BaseGeometry

from kiwitracking.campana import estado_frio_de_campana
from kiwitracking.clima import calcular_clima
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.io import a_wgs84, cruzar_con_malla, leer_csv, leer_poligono_geojson
from kiwitracking.resultado import Advertencia, ErrorDeEntrada
from kiwitracking.visualizacion import crear_mapa, preparar_mapa


@dataclass
class SolicitudAnalisis:
    """Lo que pidió el comando `analizar`, ya interpretado: solo los valores indicados (RF-8, RF-9, RF-11, RF-24).

    Los parámetros que no se indican no figuran: sus valores por defecto son los de `analizar()` y
    `ParametrosClima`, que quedan como única definición.
    """

    huella: str
    clima: str | None
    estado_frio: str | None
    campana: int | None
    parametros_analisis: dict
    parametros_clima: dict


@dataclass
class PlantasPreparadas:
    """Las plantas con `bajo_malla` listo, y el polígono con su sistema para dibujar el mapa."""

    tabla: pd.DataFrame
    poligono: BaseGeometry | None
    crs_poligono: str | None
    advertencias: list[Advertencia] = field(default_factory=list)


def _archivo_existente(ruta) -> Path:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorDeEntrada(f"No existe el archivo {ruta.name} (ruta: {ruta}).")
    if not ruta.is_file():
        raise ErrorDeEntrada(f"{ruta.name} no es un archivo (ruta: {ruta}).")
    return ruta


def preparar_plantas(
    ruta_plantas, ruta_malla, crs_plantas: str | None, columna_x: str = "X", columna_y: str = "Y"
) -> PlantasPreparadas:
    """Lee las plantas y deja `bajo_malla` listo (RF-2 a RF-5).

    Con malla, `bajo_malla` sale del cruce (y reemplaza el del CSV, si lo traía); sin malla se usa la
    columna del CSV. Las dos órdenes (`mapa` y `analizar`) pasan por acá, para que la huella coincida.
    """
    if ruta_malla is not None and (crs_plantas is None or not str(crs_plantas).strip()):
        raise ErrorDeEntrada(
            "Con --malla hace falta declarar el sistema de coordenadas de las plantas con --crs-plantas "
            "(por ejemplo, EPSG:4326)."
        )
    tabla = leer_csv(_archivo_existente(ruta_plantas))

    if ruta_malla is None:
        if "bajo_malla" not in tabla.columns:
            raise ErrorDeEntrada(
                "No se puede saber qué plantas están bajo malla: indicá la malla con --malla "
                "o agregá la columna bajo_malla al CSV de plantas."
            )
        return PlantasPreparadas(tabla, None, None)

    poligono, crs_poligono = leer_poligono_geojson(_archivo_existente(ruta_malla))
    bajo_malla, advertencias = cruzar_con_malla(tabla, poligono, crs_plantas, crs_poligono, columna_x, columna_y)

    if "bajo_malla" in tabla.columns:
        cambiaron = int((pd.to_numeric(tabla["bajo_malla"], errors="coerce") != bajo_malla).sum())
        if cambiaron:
            advertencias.append(
                Advertencia(
                    "BAJO_MALLA_REEMPLAZADO",
                    f"El CSV ya traía bajo_malla: se usó el calculado con la malla, que difiere en {cambiaron} plantas.",
                )
            )
    tabla = tabla.assign(bajo_malla=bajo_malla)
    return PlantasPreparadas(tabla, poligono, crs_poligono, advertencias)


@dataclass
class ResultadoMapa:
    """Lo que informa el comando `mapa`: la huella del lote, los grupos y los avisos."""

    ruta: Path
    huella: str
    n_bajo_malla: int
    n_fuera_de_malla: int
    advertencias: list[Advertencia] = field(default_factory=list)


def ejecutar_mapa(
    ruta_plantas,
    ruta_malla,
    crs_plantas: str | None,
    ruta_salida,
    sin_fondo_satelital: bool = False,
    sobrescribir: bool = False,
    columna_x: str = "X",
    columna_y: str = "Y",
) -> ResultadoMapa:
    """Genera el mapa de verificación y devuelve la huella del lote (RF-6, RF-7, RF-23).

    El mapa se dibuja con plantas y polígono convertidos a EPSG:4326; la conversión es solo para dibujar y no
    cambia `bajo_malla` ni la huella. No crea nada si algo falla antes de dibujar.
    """
    salida = Path(ruta_salida)
    if salida.is_dir():
        raise ErrorDeEntrada(f"{salida.name} es una carpeta: indicá un archivo HTML para el mapa.")
    if salida.exists() and not sobrescribir:
        raise ErrorDeEntrada(f"El archivo {salida.name} ya existe: usá --sobrescribir para reemplazarlo.")

    preparadas = preparar_plantas(ruta_plantas, ruta_malla, crs_plantas, columna_x, columna_y)
    plantas, poligono = a_wgs84(preparadas.tabla, preparadas.poligono, crs_plantas, preparadas.crs_poligono, columna_x, columna_y)
    datos = preparar_mapa(plantas, poligono, columna_x, columna_y)
    mapa = crear_mapa(datos, fondo_satelital=not sin_fondo_satelital)

    salida.parent.mkdir(parents=True, exist_ok=True)
    mapa.save(str(salida))
    return ResultadoMapa(
        ruta=salida,
        huella=datos.huella,
        n_bajo_malla=datos.n_bajo_malla,
        n_fuera_de_malla=datos.n_fuera_de_malla,
        advertencias=preparadas.advertencias + datos.advertencias,
    )


@dataclass
class EstadoDeFrio:
    """El estado de frío que alimenta el análisis y de dónde salió: `clima`, `manual` o `ninguno` (RF-10 a RF-14)."""

    origen: str
    estado: str | None = None
    periodo: int | None = None
    horas: float | None = None
    cobertura: float | None = None
    hueco_maximo: int | None = None
    advertencias: list[Advertencia] = field(default_factory=list)


def elegir_estado_de_frio(clima, estado_frio: str | None, campana: int | None, parametros_clima: dict) -> EstadoDeFrio:
    """El estado de frío de la última campaña: del clima (spec 002), escrito a mano o ninguno (RF-10 a RF-14).

    Con clima, `ParametrosClima` se arma solo con los valores indicados. Si ninguna ventana es clasificable no
    se detiene: no hay estado (origen `ninguno`) y el aviso explica por qué. Las advertencias van en el orden
    de RF-14: primero las del clima y después las de la elección de campaña.
    """
    if clima is None:
        return EstadoDeFrio("manual", estado_frio) if estado_frio is not None else EstadoDeFrio("ninguno")

    tabla = leer_csv(_archivo_existente(clima))
    resultado = calcular_clima(tabla, ParametrosClima(**parametros_clima, campana=campana))
    elegido = estado_frio_de_campana(resultado, campana)
    return EstadoDeFrio(
        origen="clima" if elegido.estado is not None else "ninguno",
        estado=elegido.estado,
        periodo=elegido.periodo,
        horas=elegido.horas,
        cobertura=elegido.cobertura,
        hueco_maximo=elegido.hueco_maximo,
        advertencias=resultado.advertencias + elegido.advertencias,
    )
