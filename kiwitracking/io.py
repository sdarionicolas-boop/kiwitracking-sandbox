"""Capa de entrada y salida: lectura de archivos y cruces con geometrías. El núcleo no la importa."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from kiwitracking.resultado import Advertencia, ErrorDeEntrada

COLUMNAS_CATEGORIAS = ("ambiente", "recomendacion", "estado_frio", "estado_frio_ultima_campana")
# Rastros típicos de un UTF-8 leído como Windows-1252 y vuelto a guardar (p. ej. "Óptimo" -> "Ã“ptimo").
SECUENCIAS_CORRUPTAS = ("Ã", "Â", "â€")


def leer_csv(ruta: str | Path) -> pd.DataFrame:
    """Lee un CSV como UTF-8 (RF-3). Tolera el BOM que agrega Excel al guardar como UTF-8."""
    ruta = Path(ruta)
    try:
        tabla = pd.read_csv(ruta, encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ErrorDeEntrada(
            f"El archivo {ruta.name} no está en UTF-8 (problema de codificación en el byte {error.start}). "
            "Guardalo como UTF-8 e intentá de nuevo."
        ) from error
    _revisar_categorias(tabla, ruta)
    return tabla


def _revisar_categorias(tabla: pd.DataFrame, ruta: Path) -> None:
    """RF-4: texto corrupto en las columnas de categorías. Otras columnas no se revisan."""
    for columna in COLUMNAS_CATEGORIAS:
        if columna not in tabla.columns:
            continue
        for valor in tabla[columna].dropna().astype(str):
            if any(secuencia in valor for secuencia in SECUENCIAS_CORRUPTAS):
                raise ErrorDeEntrada(
                    f"El archivo {ruta.name} tiene texto con codificación corrupta en la columna "
                    f"{columna}: {valor!r}. Corregí el archivo y guardalo como UTF-8."
                )


def calcular_bajo_malla(
    plantas: pd.DataFrame,
    poligono: BaseGeometry,
    crs_plantas: str | None,
    crs_poligono: str | None,
    columna_x: str = "X",
    columna_y: str = "Y",
) -> pd.Series:
    """`bajo_malla` por punto en polígono (RF-17): 1 si la planta cae dentro (el borde cuenta), 0 si no.

    Plantas y polígono deben declarar su sistema de coordenadas (RF-18); si difieren, el polígono
    se convierte al de las plantas antes del cruce.
    """
    for nombre, crs in (("de las plantas", crs_plantas), ("del polígono", crs_poligono)):
        if crs is None or not str(crs).strip():
            raise ErrorDeEntrada(f"Falta declarar el sistema de coordenadas {nombre} (por ejemplo, 'EPSG:4326').")

    faltan = [columna for columna in (columna_x, columna_y) if columna not in plantas.columns]
    if faltan:
        raise ErrorDeEntrada(f"Faltan las columnas de coordenadas: {columna_x}, {columna_y} (no están: {', '.join(faltan)}).")

    x, y = plantas[columna_x], plantas[columna_y]
    sin_coordenadas = int((x.isna() | y.isna()).sum())
    if sin_coordenadas:
        raise ErrorDeEntrada(f"{sin_coordenadas} plantas sin coordenadas: no se puede decidir si están bajo malla.")

    if str(crs_plantas).strip() != str(crs_poligono).strip():
        convertir = Transformer.from_crs(str(crs_poligono).strip(), str(crs_plantas).strip(), always_xy=True)
        poligono = shapely.transform(
            poligono, lambda coordenadas: np.column_stack(convertir.transform(coordenadas[:, 0], coordenadas[:, 1]))
        )

    dentro = shapely.covers(poligono, shapely.points(x.to_numpy(), y.to_numpy()))
    return pd.Series(dentro.astype(int), index=plantas.index, name="bajo_malla")


def cruzar_con_malla(
    plantas: pd.DataFrame,
    poligono: BaseGeometry,
    crs_plantas: str | None,
    crs_poligono: str | None,
    columna_x: str = "X",
    columna_y: str = "Y",
) -> tuple[pd.Series, list[Advertencia]]:
    """Como `calcular_bajo_malla`, y avisa si el cruce es sospechoso (RF-19).

    Con un polígono no vacío, que ninguna planta o todas caigan dentro suele ser un error de
    coordenadas, no un lote sin malla: el resultado se devuelve igual, pero no en silencio.
    """
    bajo_malla = calcular_bajo_malla(plantas, poligono, crs_plantas, crs_poligono, columna_x, columna_y)

    advertencias = []
    if not poligono.is_empty and bajo_malla.nunique() < 2:
        todas = bool(bajo_malla.iloc[0]) if len(bajo_malla) else False
        que = "todas las plantas" if todas else "ninguna planta"
        advertencias.append(
            Advertencia(
                "POSIBLE_ERROR_COORDENADAS",
                f"El cruce con el polígono dio que {que} está bajo malla: revisá que las coordenadas "
                "de las plantas y del polígono estén en el sistema declarado.",
            )
        )
    return bajo_malla, advertencias


def leer_poligono_geojson(ruta: str | Path) -> tuple[BaseGeometry, str]:
    """Lee los polígonos de un GeoJSON y devuelve (geometría unida, sistema de coordenadas).

    Sin miembro `crs`, el estándar GeoJSON indica WGS84 (EPSG:4326).
    """
    ruta = Path(ruta)
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ErrorDeEntrada(f"El archivo {ruta.name} no es un GeoJSON válido: {error}.") from error

    if contenido.get("type") == "FeatureCollection":
        geometrias = [feature.get("geometry") for feature in contenido.get("features", [])]
    elif contenido.get("type") == "Feature":
        geometrias = [contenido.get("geometry")]
    else:
        geometrias = [contenido]

    poligonos = [
        geometria
        for geometria in (shape(g) for g in geometrias if g)
        if geometria.geom_type in ("Polygon", "MultiPolygon")
    ]
    if not poligonos:
        raise ErrorDeEntrada(f"El archivo {ruta.name} no contiene ningún polígono.")

    crs = (contenido.get("crs") or {}).get("properties", {}).get("name") or "EPSG:4326"
    return unary_union(poligonos), crs


WGS84 = "EPSG:4326"


def _sistema(crs: str | None) -> CRS | None:
    """El sistema de coordenadas declarado, o `None` si no se declaró. Un nombre desconocido es un error."""
    if crs is None or not str(crs).strip():
        return None
    try:
        return CRS.from_user_input(str(crs).strip())
    except CRSError as error:
        raise ErrorDeEntrada(
            f"El sistema de coordenadas {str(crs).strip()!r} no se reconoce. Usá un código como 'EPSG:4326'."
        ) from error


def a_wgs84(
    plantas: pd.DataFrame,
    poligono: BaseGeometry | None,
    crs_plantas: str | None,
    crs_poligono: str | None,
    columna_x: str = "X",
    columna_y: str = "Y",
) -> tuple[pd.DataFrame, BaseGeometry | None]:
    """Plantas y polígono en longitud y latitud (EPSG:4326), solo para dibujar el mapa (RF-23).

    Devuelve copias: no modifica la tabla de entrada ni toca `bajo_malla`, la huella o el análisis.
    Un sistema no declarado (`None`) se toma como longitud y latitud y no se convierte. Una coordenada
    vacía sigue vacía, no se vuelve infinita.
    """
    destino = CRS.from_user_input(WGS84)
    origen_plantas, origen_poligono = _sistema(crs_plantas), _sistema(crs_poligono)  # validan los dos antes de convertir

    convertidas = plantas.copy()
    if origen_plantas is not None and not origen_plantas.equals(destino, ignore_axis_order=True):
        ida = Transformer.from_crs(origen_plantas, destino, always_xy=True)
        x = plantas[columna_x].to_numpy(dtype=float)
        y = plantas[columna_y].to_numpy(dtype=float)
        validas = ~(np.isnan(x) | np.isnan(y))
        x_nuevo, y_nuevo = np.full(len(x), np.nan), np.full(len(y), np.nan)
        x_nuevo[validas], y_nuevo[validas] = ida.transform(x[validas], y[validas])
        convertidas[columna_x], convertidas[columna_y] = x_nuevo, y_nuevo

    if poligono is not None and origen_poligono is not None and not origen_poligono.equals(destino, ignore_axis_order=True):
        ida = Transformer.from_crs(origen_poligono, destino, always_xy=True)
        poligono = shapely.transform(poligono, lambda coordenadas: np.column_stack(ida.transform(coordenadas[:, 0], coordenadas[:, 1])))
    return convertidas, poligono
