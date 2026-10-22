"""Capa visual: el mapa de verificación de las plantas bajo malla. El núcleo no la importa."""

from dataclasses import dataclass
from pathlib import Path

import folium
import pandas as pd
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada

COLOR_BAJO_MALLA = "#f39c12"
COLOR_FUERA_DE_MALLA = "#27ae60"


@dataclass(frozen=True)
class PuntoMapa:
    id: object
    x: float
    y: float
    bajo_malla: int
    color: str


@dataclass(frozen=True)
class DatosMapa:
    """Lo que el mapa muestra, separado de cómo se dibuja: así se puede probar sin abrir un navegador."""

    puntos: list[PuntoMapa]
    poligono: BaseGeometry | None
    huella: str
    n_bajo_malla: int
    n_fuera_de_malla: int


def preparar_mapa(
    plantas: pd.DataFrame,
    poligono: BaseGeometry | None,
    columna_x: str = "X",
    columna_y: str = "Y",
) -> DatosMapa:
    """Datos del mapa de verificación (RF-15) y la huella de la tabla (RF-16).

    Las coordenadas deben estar en longitud/latitud (EPSG:4326), que es lo que dibuja el mapa.
    """
    necesarias = ["id", "bajo_malla", columna_x, columna_y]
    faltan = [columna for columna in necesarias if columna not in plantas.columns]
    if faltan:
        raise ErrorDeEntrada(f"Faltan columnas para el mapa: {', '.join(faltan)}.")

    x, y = plantas[columna_x], plantas[columna_y]
    sin_coordenadas = int((x.isna() | y.isna()).sum())
    if sin_coordenadas:
        raise ErrorDeEntrada(f"{sin_coordenadas} plantas sin coordenadas: no se pueden dibujar en el mapa.")
    if not (x.between(-180, 180).all() and y.between(-90, 90).all()):
        raise ErrorDeEntrada(
            f"Las coordenadas de {columna_x} y {columna_y} no parecen longitud/latitud: "
            "el mapa necesita coordenadas en EPSG:4326."
        )
    if not plantas["bajo_malla"].isin([0, 1]).all():
        raise ErrorDeEntrada("La columna bajo_malla solo admite los valores 0 y 1 (sin vacíos).")

    puntos = [
        PuntoMapa(
            id=identificador,
            x=float(px),
            y=float(py),
            bajo_malla=int(bajo),
            color=COLOR_BAJO_MALLA if bajo == 1 else COLOR_FUERA_DE_MALLA,
        )
        for identificador, px, py, bajo in zip(plantas["id"], x, y, plantas["bajo_malla"])
    ]
    n_bajo = int((plantas["bajo_malla"] == 1).sum())
    return DatosMapa(
        puntos=puntos,
        poligono=poligono,
        huella=huella(plantas),
        n_bajo_malla=n_bajo,
        n_fuera_de_malla=len(plantas) - n_bajo,
    )


ESRI_TESELAS = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_ATRIBUCION = "Esri, Maxar, Earthstar Geographics"


def crear_mapa(datos: DatosMapa, fondo_satelital: bool = True) -> folium.Map:
    """Dibuja los datos del mapa (RF-15). Armarlo no usa internet; el fondo se pide al abrir el HTML."""
    latitud = sum(p.y for p in datos.puntos) / len(datos.puntos)
    longitud = sum(p.x for p in datos.puntos) / len(datos.puntos)
    mapa = folium.Map(location=(latitud, longitud), zoom_start=17, tiles=None)
    if fondo_satelital:
        folium.TileLayer(tiles=ESRI_TESELAS, attr=ESRI_ATRIBUCION, name="Imagen satelital (Esri)").add_to(mapa)

    if datos.poligono is not None:
        folium.GeoJson(
            mapping(datos.poligono),
            name="Zona bajo malla",
            style_function=lambda _: {"color": COLOR_BAJO_MALLA, "weight": 2, "fillOpacity": 0.08},
        ).add_to(mapa)

    for punto in datos.puntos:
        grupo = "bajo malla" if punto.bajo_malla == 1 else "fuera de malla"
        folium.CircleMarker(
            location=(punto.y, punto.x),
            radius=4,
            color=punto.color,
            fill=True,
            fill_opacity=0.9,
            tooltip=f"Planta {punto.id}: {grupo}",
        ).add_to(mapa)

    mapa.get_root().html.add_child(folium.Element(_cuadro_de_verificacion(datos)))
    return mapa


def _cuadro_de_verificacion(datos: DatosMapa) -> str:
    return (
        '<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:white;padding:10px 14px;'
        'border:1px solid #888;border-radius:6px;font:13px sans-serif;max-width:320px">'
        "<b>Verificación de plantas bajo malla</b><br>"
        f'<span style="color:{COLOR_BAJO_MALLA}">&#9679;</span> {datos.n_bajo_malla} plantas bajo malla<br>'
        f'<span style="color:{COLOR_FUERA_DE_MALLA}">&#9679;</span> {datos.n_fuera_de_malla} plantas fuera de malla<br>'
        f"Huella de confirmación: <code>{datos.huella}</code><br>"
        "<small>Si el mapa es correcto, pasá esta huella al análisis.</small>"
        "</div>"
    )


def generar_mapa(
    plantas: pd.DataFrame,
    poligono: BaseGeometry | None,
    ruta_html: str | Path,
    columna_x: str = "X",
    columna_y: str = "Y",
    fondo_satelital: bool = True,
) -> str:
    """Guarda el mapa de verificación como HTML y devuelve la huella de la tabla (RF-15, RF-16)."""
    datos = preparar_mapa(plantas, poligono, columna_x, columna_y)
    mapa = crear_mapa(datos, fondo_satelital)

    ruta = Path(ruta_html)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    mapa.save(str(ruta))
    return datos.huella
