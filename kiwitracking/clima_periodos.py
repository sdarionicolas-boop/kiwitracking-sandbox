"""Temporadas, ventanas de frío y sus días esperados (spec 002, RF-12 y RF-13).

La campaña `Y` corresponde al período de etiqueta `Y`. Una temporada empieza el día 1 de
`mes_inicio_temporada` y dura 12 meses; la ventana de frío agrupa los días de `meses_frio` por
invierno (año calendario) o por temporada, que es el cálculo del notebook original y mezcla partes
de dos inviernos.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from kiwitracking.clima_parametros import ParametrosClima


def etiqueta_temporada(fechas: pd.Series, parametros: ParametrosClima) -> pd.Series:
    """Etiqueta de temporada de cada fecha: el año en que empieza esa temporada (RF-12)."""
    anterior = (fechas.dt.month < parametros.mes_inicio_temporada).astype(int)
    return (fechas.dt.year - anterior).astype("Int64")


def etiqueta_ventana(fechas: pd.Series, parametros: ParametrosClima) -> pd.Series:
    """Etiqueta de la ventana de frío de cada fecha, o vacío si su mes no está en `meses_frio` (RF-13)."""
    if parametros.ventana_frio == "invierno":
        etiquetas = fechas.dt.year.astype("Int64")
    else:
        etiquetas = etiqueta_temporada(fechas, parametros)
    return etiquetas.where(fechas.dt.month.isin(parametros.meses_frio))


def dias_esperados_temporada(etiqueta: int, parametros: ParametrosClima) -> pd.DatetimeIndex:
    """Todos los días de la temporada `etiqueta`, estén o no en los datos (RF-12)."""
    inicio = pd.Timestamp(year=int(etiqueta), month=parametros.mes_inicio_temporada, day=1)
    fin = inicio + pd.DateOffset(years=1) - pd.Timedelta(days=1)
    return pd.date_range(inicio, fin)


def dias_esperados_ventana(etiqueta: int, parametros: ParametrosClima) -> pd.DatetimeIndex:
    """Todos los días que tendría completa la ventana de frío `etiqueta` (RF-13)."""
    if parametros.ventana_frio == "invierno":
        dias = pd.date_range(f"{int(etiqueta)}-01-01", f"{int(etiqueta)}-12-31")
    else:
        dias = dias_esperados_temporada(etiqueta, parametros)
    return dias[dias.month.isin(parametros.meses_frio)]


COLUMNAS_COBERTURA = ["dias_disponibles", "dias_esperados", "cobertura", "hueco_maximo", "completo"]


def _racha_mas_larga(faltantes: np.ndarray) -> int:
    """Largo de la mayor racha de valores verdaderos consecutivos (días seguidos sin datos)."""
    if not faltantes.any():
        return 0
    presentes = np.flatnonzero(~faltantes)
    bordes = np.concatenate(([-1], presentes, [len(faltantes)]))
    return int(np.max(np.diff(bordes)) - 1)


def evaluar_cobertura(
    tabla: pd.DataFrame,
    etiquetas: pd.Series,
    esperados: Callable[[int], pd.DatetimeIndex],
    parametros: ParametrosClima,
) -> pd.DataFrame:
    """Cobertura, hueco máximo y si cada período es completo (RF-14, RF-15, RF-16).

    `tabla` trae `date` y `disponible`; `etiquetas` dice a qué período pertenece cada fila (o vacío);
    `esperados(etiqueta)` da todos los días que ese período tendría completo. Los días esperados
    incluyen los que quedan fuera del rango de los datos. Un período sin ningún día disponible no
    aparece. La cobertura se compara dividiendo, no multiplicando, para que el borde exacto sea completo.
    """
    con_datos = tabla["disponible"] & etiquetas.notna()
    fechas = tabla.loc[con_datos, "date"]
    etiquetas_con_datos = etiquetas[con_datos]

    filas = {}
    for etiqueta in sorted(etiquetas_con_datos.dropna().unique()):
        dias_esperados = esperados(int(etiqueta))
        presentes = np.asarray(dias_esperados.isin(fechas[etiquetas_con_datos == etiqueta]))
        disponibles = int(presentes.sum())
        cobertura = disponibles / len(dias_esperados)
        hueco = _racha_mas_larga(~presentes)
        limite = parametros.max_hueco_dias
        completo = cobertura >= parametros.cobertura_minima and (limite is None or hueco <= limite)
        filas[int(etiqueta)] = (disponibles, len(dias_esperados), cobertura, hueco, bool(completo))

    resultado = pd.DataFrame.from_dict(filas, orient="index", columns=COLUMNAS_COBERTURA)
    resultado.index.name = "etiqueta"
    return resultado.astype(
        {"dias_disponibles": "int64", "dias_esperados": "int64", "cobertura": "float64", "hueco_maximo": "int64", "completo": "bool"}
    )


def cobertura_temporadas(tabla: pd.DataFrame, parametros: ParametrosClima) -> pd.DataFrame:
    """Cobertura de cada temporada (la base del GDD, RF-14)."""
    return evaluar_cobertura(
        tabla,
        etiqueta_temporada(tabla["date"], parametros),
        lambda etiqueta: dias_esperados_temporada(etiqueta, parametros),
        parametros,
    )


def cobertura_ventanas(tabla: pd.DataFrame, parametros: ParametrosClima) -> pd.DataFrame:
    """Cobertura de cada ventana de frío, en el modo que indiquen los parámetros (RF-14)."""
    return evaluar_cobertura(
        tabla,
        etiqueta_ventana(tabla["date"], parametros),
        lambda etiqueta: dias_esperados_ventana(etiqueta, parametros),
        parametros,
    )
