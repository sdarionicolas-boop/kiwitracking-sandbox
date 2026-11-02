"""Agregación multianual del KVPI por planta (spec 004). Sin archivos, sin rutas y sin impresión."""

import re
from dataclasses import dataclass, field
from numbers import Integral

import numpy as np
import pandas as pd

from kiwitracking.resultado import Advertencia, ErrorDeEntrada

MAX_PARES_EN_EL_ERROR = 10
MIN_CAMPANAS_PERMITIDO = 2
_COMA_DECIMAL = re.compile(r"^\s*-?\d+,\d+\s*$")


@dataclass
class ResultadoKvpi:
    """Lo que devuelve `agregar_kvpi`: una fila por planta y las advertencias en orden."""

    tabla: pd.DataFrame
    advertencias: list[Advertencia] = field(default_factory=list)


def _plural(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _columna_de_campana(serie: pd.DataFrame) -> str:
    """RF-1: valida las columnas obligatorias y devuelve el nombre de la de campaña que trae la serie."""
    con_enie, sin_enie = "campaña" in serie.columns, "campana" in serie.columns
    if con_enie and sin_enie:
        raise ErrorDeEntrada("La serie trae las columnas campaña y campana a la vez: indicá una sola.")
    faltantes = [columna for columna in ("id", "KVPI") if columna not in serie.columns]
    if not (con_enie or sin_enie):
        faltantes.append("campaña (o campana)")
    if faltantes:
        raise ErrorDeEntrada(f"Faltan columnas obligatorias en la serie: {', '.join(faltantes)}.")
    return "campaña" if con_enie else "campana"


def _como_texto(columna: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Devuelve el texto sin espacios al inicio ni al final y qué filas están vacías (RF-2, RF-5)."""
    texto = columna.astype(str).str.strip()
    vacios = columna.isna() | (texto == "")
    return texto, vacios


def _kvpi_numerico(columna: pd.Series) -> pd.Series:
    """RF-3: números finitos; los vacíos quedan como NaN. Texto o infinitos detienen el proceso."""
    numerica = pd.to_numeric(columna, errors="coerce")
    no_numericos = columna[columna.notna() & numerica.isna()]
    if len(no_numericos):
        ejemplo = no_numericos.iloc[0]
        con_coma = sum(bool(_COMA_DECIMAL.match(str(valor))) for valor in no_numericos)
        causa = " Probable causa: coma decimal (usá punto)." if con_coma > 1 else ""
        raise ErrorDeEntrada(
            f"La columna KVPI contiene texto que no es un número, por ejemplo {str(ejemplo)!r}.{causa}"
        )
    infinitos = int(np.isinf(numerica.to_numpy(dtype=float)).sum())
    if infinitos:
        raise ErrorDeEntrada(f"La columna KVPI contiene {_plural(infinitos, 'valor infinito', 'valores infinitos')}.")
    return numerica.astype(float)


def validar_serie(serie: pd.DataFrame) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Valida la serie y la deja lista para agregar (RF-1 a RF-6).

    Devuelve una tabla nueva con las columnas `id`, `campana` y `KVPI`, ordenada por `id` y campaña, y las
    advertencias. No modifica la tabla de entrada. Un `KVPI` vacío es una campaña sin dato; la comparación de
    repetidos lo trata como un valor más (dos vacíos son iguales, un vacío y un número son distintos).
    """
    columna_campana = _columna_de_campana(serie)
    if serie.empty:
        raise ErrorDeEntrada("La serie está vacía: no hay filas para agregar.")

    ids, ids_vacios = _como_texto(serie["id"])
    campanas, campanas_vacias = _como_texto(serie[columna_campana])
    sin_clave = int((ids_vacios | campanas_vacias).sum())
    if sin_clave:
        raise ErrorDeEntrada(
            f"{_plural(sin_clave, 'fila', 'filas')} sin id o sin campaña: toda fila necesita las dos."
        )

    tabla = pd.DataFrame({"id": ids, "campana": campanas, "KVPI": _kvpi_numerico(serie["KVPI"])})
    tabla = tabla.sort_values(["id", "campana"], kind="mergesort").reset_index(drop=True)

    sin_repetidos = tabla.drop_duplicates()
    en_conflicto = sin_repetidos.loc[sin_repetidos.duplicated(["id", "campana"]), ["id", "campana"]]
    en_conflicto = en_conflicto.drop_duplicates()
    if len(en_conflicto):
        pares = [f"{fila.id}/{fila.campana}" for fila in en_conflicto.itertuples()]
        resto = len(pares) - MAX_PARES_EN_EL_ERROR
        mas = f" (y {resto} más)" if resto > 0 else ""
        raise ErrorDeEntrada(
            f"Hay {len(pares)} pares id/campaña con valores de KVPI distintos: "
            f"{', '.join(pares[:MAX_PARES_EN_EL_ERROR])}{mas}. "
            "Una planta no puede tener dos valores en la misma campaña: corregí la serie."
        )

    descartadas = len(tabla) - len(sin_repetidos)
    avisos = []
    if descartadas:
        mensaje = f"Se descartaron {descartadas} filas repetidas (mismo id, campaña y KVPI)."
        avisos.append(Advertencia("KVPI_DUPLICADO", mensaje))
    return sin_repetidos.reset_index(drop=True), avisos


def _validar_min_campanas(min_campanas) -> None:
    """RF-10: un entero de 2 en adelante (True y False son enteros, pero menores que 2)."""
    if not isinstance(min_campanas, Integral) or min_campanas < MIN_CAMPANAS_PERMITIDO:
        raise ErrorDeEntrada(
            f"min_campanas={min_campanas!r} no es válido. Valores permitidos: un entero mayor o igual que "
            f"{MIN_CAMPANAS_PERMITIDO}."
        )


def _avisos_por_planta(por_planta: pd.DataFrame, campanas_encontradas: int, min_campanas: int) -> list[Advertencia]:
    """RF-11 y RF-12: plantas con menos campañas que las de la serie, y plantas sin desvío por `min_campanas`."""
    avisos = []
    n = por_planta["n_campanas"]
    incompletas = n[n < campanas_encontradas]
    if len(incompletas):
        mensaje = (
            f"{_plural(len(incompletas), 'planta', 'plantas')} con menos campañas con dato que las "
            f"{campanas_encontradas} de la serie (n_campanas entre {incompletas.min()} y {incompletas.max()})."
        )
        avisos.append(Advertencia("PLANTAS_CON_MENOS_CAMPANAS", mensaje))
    sin_desvio = int((n < min_campanas).sum())
    if sin_desvio:
        mensaje = (
            f"{_plural(sin_desvio, 'planta', 'plantas')} sin desvío (KVPI_std y KVPI_cv vacíos) "
            f"por tener menos de {min_campanas} campañas con dato."
        )
        avisos.append(Advertencia("SIN_DESVIO", mensaje))
    return avisos


def agregar_kvpi(serie: pd.DataFrame, min_campanas: int = 2) -> ResultadoKvpi:
    """Agrega la serie por planta (RF-7 a RF-10): campañas con dato, promedio, desvío muestral (n−1) y CV.

    El cálculo es el de `groupby("id")["KVPI"].agg(["mean", "std", "count"])` de `pandas`. Con menos de
    `min_campanas` campañas con dato el desvío y el CV quedan vacíos; el promedio se conserva. Los `id` salen
    como texto y la tabla ordenada por `id`. No modifica la serie.
    """
    _validar_min_campanas(min_campanas)
    tabla, avisos = validar_serie(serie)

    agregado = tabla.groupby("id")["KVPI"].agg(["count", "mean", "std"])
    agregado.loc[agregado["count"] < min_campanas, "std"] = np.nan
    promedio_util = agregado["mean"].notna() & (agregado["mean"] != 0)
    cv = (agregado["std"] / agregado["mean"]).where(promedio_util)

    por_planta = pd.DataFrame(
        {
            "id": agregado.index,
            "n_campanas": agregado["count"].astype(int).to_numpy(),
            "KVPI_mean": agregado["mean"].to_numpy(),
            "KVPI_std": agregado["std"].to_numpy(),
            "KVPI_cv": cv.to_numpy(),
        }
    )
    avisos += _avisos_por_planta(por_planta, tabla["campana"].nunique(), min_campanas)
    return ResultadoKvpi(por_planta, avisos)
