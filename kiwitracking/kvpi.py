"""Agregación multianual del KVPI por planta (spec 004). Sin archivos, sin rutas y sin impresión."""

import re
from dataclasses import dataclass, field
from numbers import Integral, Real

import numpy as np
import pandas as pd

from kiwitracking.clima import formatear_porcentaje
from kiwitracking.resultado import Advertencia, ErrorDeEntrada

MAX_PARES_EN_EL_ERROR = 10
MIN_CAMPANAS_PERMITIDO = 2
_COMA_DECIMAL = re.compile(r"^\s*-?\d+,\d+\s*$")


@dataclass(frozen=True)
class CoberturaCampana:
    """RF-20: cuántas plantas tienen dato en una campaña y qué proporción son de las de referencia."""

    campana: str
    plantas_con_dato: int
    proporcion: float


@dataclass
class ResultadoKvpi:
    """Lo que devuelve `agregar_kvpi`: una fila por planta, las advertencias en orden y la cobertura por campaña."""

    tabla: pd.DataFrame
    advertencias: list[Advertencia] = field(default_factory=list)
    cobertura: list[CoberturaCampana] = field(default_factory=list)


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


def _validar_cobertura_minima(valor) -> None:
    """RF-21: un número entre 0 y 1."""
    es_numero = isinstance(valor, Real) and not isinstance(valor, bool)
    if not es_numero or not 0 <= valor <= 1:
        raise ErrorDeEntrada(
            f"cobertura_minima_campana={valor!r} no es válido. Valores permitidos: un número entre 0 y 1."
        )


def _validar_total_plantas(total) -> None:
    """RF-20: las plantas de referencia, si se indican, son un entero positivo."""
    if total is None:
        return
    if isinstance(total, bool) or not isinstance(total, Integral) or total < 1:
        raise ErrorDeEntrada(
            f"total_plantas={total!r} no es válido. Valores permitidos: un entero mayor o igual que 1."
        )


def _etiquetas_esperadas(campanas) -> list[str]:
    """RF-22: la lista de campañas esperadas, sin espacios al inicio ni al final, sin vacías ni repetidas."""
    if isinstance(campanas, str) or not hasattr(campanas, "__iter__"):
        raise ErrorDeEntrada("Las campañas esperadas deben ser una lista de etiquetas, no un solo texto.")
    etiquetas = [str(etiqueta).strip() for etiqueta in campanas]
    if not etiquetas:
        raise ErrorDeEntrada("La lista de campañas esperadas está vacía.")
    if "" in etiquetas:
        raise ErrorDeEntrada("La lista de campañas esperadas tiene una etiqueta vacía.")
    repetidas = sorted({etiqueta for etiqueta in etiquetas if etiquetas.count(etiqueta) > 1})
    if repetidas:
        raise ErrorDeEntrada(f"La lista de campañas esperadas repite etiquetas: {', '.join(repetidas)}.")
    return etiquetas


def _comparar_con_esperadas(encontradas: list[str], esperadas: list[str]) -> None:
    """RF-22: la lista esperada y las etiquetas de la serie tienen que ser las mismas."""
    faltan = [etiqueta for etiqueta in esperadas if etiqueta not in encontradas]
    sobran = [etiqueta for etiqueta in encontradas if etiqueta not in esperadas]
    if not (faltan or sobran):
        return
    partes = []
    if faltan:
        partes.append(f"no aparecen en la serie: {', '.join(faltan)}")
    if sobran:
        partes.append(f"no estaban entre las esperadas: {', '.join(sobran)}")
    raise ErrorDeEntrada(f"Las campañas esperadas no coinciden con las de la serie ({'; '.join(partes)}).")


def _cobertura_por_campana(
    tabla: pd.DataFrame, etiquetas: list[str], total_plantas: int | None, minimo: float
) -> tuple[list[CoberturaCampana], list[Advertencia]]:
    """RF-20 y RF-21: plantas con dato por campaña, su proporción y un aviso por cada una por debajo del mínimo."""
    total = total_plantas if total_plantas is not None else tabla["id"].nunique()
    con_dato = tabla[tabla["KVPI"].notna()].groupby("campana")["id"].nunique()
    cobertura = [
        CoberturaCampana(etiqueta, int(con_dato.get(etiqueta, 0)), int(con_dato.get(etiqueta, 0)) / total)
        for etiqueta in etiquetas
    ]
    avisos = [
        Advertencia(
            "CAMPANA_CON_POCOS_DATOS",
            f"La campaña {c.campana} tiene dato en {c.plantas_con_dato} de {total} plantas "
            f"({formatear_porcentaje(c.proporcion)}), por debajo del mínimo de {formatear_porcentaje(minimo)}.",
        )
        for c in cobertura
        if c.proporcion < minimo
    ]
    return cobertura, avisos


def agregar_kvpi(
    serie: pd.DataFrame,
    min_campanas: int = 2,
    campanas: list[str] | None = None,
    cobertura_minima_campana: float = 0.5,
    total_plantas: int | None = None,
) -> ResultadoKvpi:
    """Agrega la serie por planta (RF-7 a RF-10): campañas con dato, promedio, desvío muestral (n−1) y CV.

    El cálculo es el de `groupby("id")["KVPI"].agg(["mean", "std", "count"])` de `pandas`. Con menos de
    `min_campanas` campañas con dato el desvío y el CV quedan vacíos; el promedio se conserva. Los `id` salen
    como texto y la tabla ordenada por `id`. No modifica la serie.
    """
    _validar_min_campanas(min_campanas)
    _validar_cobertura_minima(cobertura_minima_campana)
    _validar_total_plantas(total_plantas)
    esperadas = None if campanas is None else _etiquetas_esperadas(campanas)
    tabla, avisos = validar_serie(serie)
    etiquetas = sorted(tabla["campana"].unique())
    if esperadas is not None:
        _comparar_con_esperadas(etiquetas, esperadas)

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
    avisos += _avisos_por_planta(por_planta, len(etiquetas), min_campanas)
    cobertura, avisos_cobertura = _cobertura_por_campana(tabla, etiquetas, total_plantas, cobertura_minima_campana)
    return ResultadoKvpi(por_planta, avisos + avisos_cobertura, cobertura)


COLUMNAS_RESULTADO = ("id", "KVPI_mean", "KVPI_std", "KVPI_cv", "n_campanas")
MENSAJE_HUELLA = (
    "La huella de `mapa` depende de qué plantas quedan en el resultado: si cambia entre dos corridas, "
    "revisá primero esta advertencia."
)


def _nombrar_ids(ids: list[str]) -> str:
    """Hasta 10 `id` separados por coma y cuántos más hay."""
    resto = len(ids) - MAX_PARES_EN_EL_ERROR
    mas = f" (y {resto} más)" if resto > 0 else ""
    return f"{', '.join(ids[:MAX_PARES_EN_EL_ERROR])}{mas}"


def _preparar_muestreo(muestreo: pd.DataFrame) -> tuple[pd.DataFrame, list[Advertencia]]:
    """RF-14: valida el muestreo y deja `id` como texto, `X` e `Y` como números y un solo registro por `id`."""
    faltantes = [columna for columna in ("id", "X", "Y") if columna not in muestreo.columns]
    if faltantes:
        raise ErrorDeEntrada(f"Faltan columnas obligatorias en el muestreo: {', '.join(faltantes)}.")
    if muestreo.empty:
        raise ErrorDeEntrada("El muestreo está vacío: no hay plantas con coordenadas.")

    ids, ids_vacios = _como_texto(muestreo["id"])
    sin_id = int(ids_vacios.sum())
    if sin_id:
        raise ErrorDeEntrada(f"{_plural(sin_id, 'fila', 'filas')} del muestreo sin id: toda planta necesita un id.")

    tabla = muestreo.copy()
    tabla["id"] = ids
    for columna in ("X", "Y"):
        numerica = pd.to_numeric(tabla[columna], errors="coerce")
        no_numericos = tabla[columna][tabla[columna].notna() & numerica.isna()]
        if len(no_numericos):
            raise ErrorDeEntrada(
                f"La columna {columna} del muestreo contiene texto que no es un número, "
                f"por ejemplo {str(no_numericos.iloc[0])!r}."
            )
        tabla[columna] = numerica

    unicas = tabla.drop_duplicates()
    en_conflicto = unicas.loc[unicas["id"].duplicated(), "id"].drop_duplicates().tolist()
    if en_conflicto:
        raise ErrorDeEntrada(
            f"Hay {len(en_conflicto)} id repetidos en el muestreo con valores distintos: "
            f"{_nombrar_ids(en_conflicto)}. Una planta no puede tener dos conjuntos de datos: corregí el archivo."
        )
    avisos = []
    descartadas = len(tabla) - len(unicas)
    if descartadas:
        mensaje = f"Se descartaron {_plural(descartadas, 'fila repetida', 'filas repetidas')} del muestreo."
        avisos.append(Advertencia("MUESTREO_DUPLICADO", mensaje))
    return unicas.reset_index(drop=True), avisos


def unir_con_muestreo(por_planta: pd.DataFrame, muestreo: pd.DataFrame) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Une el resultado por planta con el muestreo (RF-13, RF-14).

    Devuelve solo las plantas que están en los dos, en el orden del muestreo, con `id`, `KVPI_mean`, `KVPI_std`,
    `KVPI_cv`, `n_campanas` y después las demás columnas del muestreo. Los `id` se comparan como texto. Una
    columna del muestreo con el nombre de una de resultado se reemplaza por la calculada. No modifica las tablas.
    """
    tabla, avisos = _preparar_muestreo(muestreo)
    con_coordenadas = tabla["X"].notna() & tabla["Y"].notna()
    ids_de_la_serie = set(por_planta["id"])
    ids_con_coordenadas = set(tabla.loc[con_coordenadas, "id"])

    sin_coordenadas = [i for i in por_planta["id"] if i not in ids_con_coordenadas]
    if sin_coordenadas:
        mensaje = (
            f"{_plural(len(sin_coordenadas), 'planta', 'plantas')} de la serie sin coordenadas en el muestreo "
            f"quedan fuera: {_nombrar_ids(sin_coordenadas)}."
        )
        avisos.append(Advertencia("PLANTAS_SIN_COORDENADAS", mensaje))
    sin_serie = [i for i in tabla["id"] if i not in ids_de_la_serie]
    if sin_serie:
        mensaje = (
            f"{_plural(len(sin_serie), 'planta', 'plantas')} del muestreo sin serie quedan fuera: "
            f"{_nombrar_ids(sin_serie)}. {MENSAJE_HUELLA}"
        )
        avisos.append(Advertencia("PLANTAS_SIN_SERIE", mensaje))

    en_comun = tabla[con_coordenadas & tabla["id"].isin(ids_de_la_serie)]
    if en_comun.empty:
        raise ErrorDeEntrada(
            "Ninguna planta de la serie está en el muestreo con coordenadas. "
            "Revisá que los id sean los mismos en los dos archivos."
        )
    del_muestreo = [columna for columna in tabla.columns if columna != "id" and columna not in COLUMNAS_RESULTADO]
    unidas = en_comun[["id", *del_muestreo]].merge(por_planta, on="id", how="left")
    return unidas[[*COLUMNAS_RESULTADO, *del_muestreo]].reset_index(drop=True), avisos
