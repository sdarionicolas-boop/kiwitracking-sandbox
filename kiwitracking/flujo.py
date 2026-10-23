"""Flujo de la línea de comandos sin consola (spec 003): une las piezas de las specs 001 y 002.

No importa `argparse` ni imprime: recibe valores y devuelve datos, para probarse sin consola. No calcula
nada propio: lee archivos y llama a las funciones que ya existen.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from shapely.geometry.base import BaseGeometry

from kiwitracking.io import cruzar_con_malla, leer_csv, leer_poligono_geojson
from kiwitracking.resultado import Advertencia, ErrorDeEntrada


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
