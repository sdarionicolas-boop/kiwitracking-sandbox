"""Capa de entrada y salida: lectura de archivos y cruces con geometrías. El núcleo no la importa."""

from pathlib import Path

import pandas as pd

from kiwitracking.resultado import ErrorDeEntrada

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
