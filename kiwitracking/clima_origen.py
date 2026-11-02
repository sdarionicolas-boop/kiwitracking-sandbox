"""Recuento de los días estimados (por ejemplo, interpolados) de cada ventana de frío (spec 005)."""

import pandas as pd

from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.clima_periodos import etiqueta_ventana

COLUMNAS_ESTIMADOS = ["periodo", "dias_estimados", "proporcion_estimada"]
_TIPOS = {"periodo": "int64", "dias_estimados": "int64", "proporcion_estimada": "float64"}


def estimados_vacios() -> pd.DataFrame:
    """La tabla de recuentos sin filas, con sus columnas y tipos."""
    return pd.DataFrame({columna: pd.Series(dtype=tipo) for columna, tipo in _TIPOS.items()})


def contar_estimados(tabla: pd.DataFrame, parametros: ParametrosClima) -> pd.DataFrame:
    """Días estimados y su proporción, por ventana de frío (RF-1, RF-2, RF-3).

    `tabla` es la tabla preparada con `preparar_clima_con_origen`. Una fila por cada ventana con al menos un día
    disponible, ordenada por período (la agrupación ya la ordena); la proporción es sobre los días disponibles de la ventana. Sin la columna
    `estimado` (el clima no trae `origen`) no hay filas.
    """
    if "estimado" not in tabla.columns:
        return estimados_vacios()

    disponibles = tabla[tabla["disponible"]]
    etiquetas = etiqueta_ventana(disponibles["date"], parametros)
    grupos = disponibles.groupby(etiquetas)  # los días fuera de las ventanas tienen etiqueta vacía y se descartan
    dias = grupos.size()
    estimados = grupos["estimado"].sum()
    resultado = pd.DataFrame(
        {"periodo": dias.index, "dias_estimados": estimados.to_numpy(), "proporcion_estimada": (estimados / dias).to_numpy()}
    )
    return resultado.astype(_TIPOS)
