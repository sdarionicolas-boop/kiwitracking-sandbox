"""Validación y normalización de la tabla diaria de temperaturas (spec 002, RF-1 a RF-8)."""

import datetime
import re
from numbers import Real

import pandas as pd

from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import Advertencia, ErrorDeEntrada

COLUMNAS_OBLIGATORIAS = ("date", "Tmax", "Tmin")
COLUMNAS_TEMPERATURA = ("Tmax", "Tmin")

_COMA_DECIMAL = re.compile(r"^\s*-?\d+,\d+\s*$")
# AAAA-MM-DD, con o sin hora o zona a continuación (separada por espacio o por T).
_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ].*)?$")


def validar_columnas_y_temperaturas(tabla: pd.DataFrame) -> None:
    """Columnas obligatorias, tabla no vacía y temperaturas numéricas (RF-1, RF-3). No modifica la tabla.

    Los valores vacíos no son un error: un día sin temperatura es un día faltante (RF-7).
    """
    faltantes = [columna for columna in COLUMNAS_OBLIGATORIAS if columna not in tabla.columns]
    if faltantes:
        raise ErrorDeEntrada(f"Faltan columnas obligatorias: {', '.join(faltantes)}.")

    if tabla.empty:
        raise ErrorDeEntrada("La tabla de clima está vacía: no hay días para analizar.")

    for columna in COLUMNAS_TEMPERATURA:
        _validar_numerica(tabla[columna], columna)


def _validar_numerica(valores: pd.Series, nombre: str) -> None:
    if pd.api.types.is_numeric_dtype(valores):
        return
    presentes = valores.dropna()
    if all(isinstance(v, Real) and not isinstance(v, bool) for v in presentes):
        return  # columna de objetos con números y vacíos, o toda vacía

    mensaje = f"La columna {nombre} contiene valores no numéricos."
    if any(isinstance(v, str) and _COMA_DECIMAL.match(v) for v in presentes):
        mensaje += " Parece que usa coma decimal (por ejemplo '27,4'): usá punto decimal."
    raise ErrorDeEntrada(mensaje)


def normalizar_fechas(fechas: pd.Series, formato_fecha: str | None = None) -> pd.Series:
    """Devuelve la columna `date` como fechas de un día, sin hora (RF-2). No modifica la entrada.

    Por defecto el texto debe ser AAAA-MM-DD, con o sin hora o zona; se toma el día tal como está
    escrito, sin convertir de zona. Con `formato_fecha` se lee exactamente con ese formato. Nunca se
    infiere el formato. Las fechas vacías o ilegibles son un error con la cantidad y un ejemplo.
    """
    if pd.api.types.is_datetime64_any_dtype(fechas.dtype):
        sin_zona = fechas.dt.tz_localize(None) if fechas.dt.tz is not None else fechas
        resultado = sin_zona.dt.normalize()
        invalidas = fechas[resultado.isna()]
    else:
        dias = [_a_dia(valor, formato_fecha) for valor in fechas]
        resultado = pd.Series(pd.to_datetime(pd.Series(dias, index=fechas.index, dtype=object)), index=fechas.index)
        invalidas = fechas[resultado.isna()]

    if len(invalidas):
        raise ErrorDeEntrada(_mensaje_fechas_invalidas(invalidas, formato_fecha))
    return resultado


def _a_dia(valor, formato_fecha: str | None):
    """El día de un valor, o None si está vacío o no se puede leer."""
    if valor is None or valor is pd.NaT or (isinstance(valor, float) and valor != valor):
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None
        try:
            if formato_fecha is not None:
                return datetime.datetime.strptime(texto, formato_fecha).date()
            coincide = _ISO.match(texto)
            return datetime.datetime.strptime(coincide.group(1), "%Y-%m-%d").date() if coincide else None
        except ValueError:
            return None
    if isinstance(valor, (datetime.date, datetime.datetime, pd.Timestamp)):
        momento = pd.Timestamp(valor)
        return (momento.tz_localize(None) if momento.tzinfo is not None else momento).date()
    return None  # números u otros tipos: no son fechas


def _mensaje_fechas_invalidas(invalidas: pd.Series, formato_fecha: str | None) -> str:
    cantidad = len(invalidas)
    primera = invalidas.iloc[0]
    vacia = primera is None or primera is pd.NaT or (isinstance(primera, float) and primera != primera)
    vacia = vacia or (isinstance(primera, str) and not primera.strip())
    ejemplo = "un valor vacío" if vacia else repr(primera)
    esperado = f"el formato {formato_fecha!r}" if formato_fecha else "AAAA-MM-DD (con o sin hora o zona)"
    sustantivo = "fecha" if cantidad == 1 else "fechas"
    return f"{cantidad} {sustantivo} vacías o ilegibles. Ejemplo: {ejemplo}. Se espera {esperado}."


MAX_FECHAS_EN_EL_ERROR = 10


def descartar_fechas_duplicadas(tabla: pd.DataFrame) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Fechas repetidas con las mismas temperaturas: se conserva la primera y se avisa (RF-4).

    La misma fecha con temperaturas distintas es un error. Solo cuentan `date`, `Tmax` y `Tmin`;
    las demás columnas se ignoran y se conserva la de la primera aparición. Los vacíos se
    consideran iguales entre sí. Espera `date` ya normalizada (`normalizar_fechas`).
    """
    claves = tabla[["date", "Tmax", "Tmin"]]
    repetidas = claves[claves["date"].duplicated(keep=False)]
    distintas = repetidas.drop_duplicates()
    en_conflicto = distintas.loc[distintas["date"].duplicated(), "date"].drop_duplicates().tolist()
    if en_conflicto:
        nombradas = ", ".join(f"{pd.Timestamp(f):%Y-%m-%d}" for f in en_conflicto[:MAX_FECHAS_EN_EL_ERROR])
        resto = len(en_conflicto) - MAX_FECHAS_EN_EL_ERROR
        mas = f" (y {resto} más)" if resto > 0 else ""
        raise ErrorDeEntrada(
            f"Hay {len(en_conflicto)} fechas repetidas con temperaturas distintas: {nombradas}{mas}. "
            "Un mismo día no puede tener dos pares de temperaturas: corregí el archivo."
        )

    descartadas = claves.duplicated(keep="first")
    cantidad = int(descartadas.sum())
    if cantidad == 0:
        return tabla.copy(), []
    mensaje = f"Se descartaron {cantidad} filas con fecha repetida y las mismas temperaturas."
    return tabla[~descartadas].copy(), [Advertencia("FECHA_DUPLICADA", mensaje)]


def validar_temperaturas_plausibles(tabla: pd.DataFrame, rango_fisico: tuple = (-60, 60)) -> None:
    """Rechaza temperaturas imposibles: fuera del rango físico (RF-6) o con Tmax menor que Tmin (RF-5).

    Primero se revisa el rango, porque un valor imposible (por ejemplo, -999) explica mejor la causa
    que la inversión que provoca. Tmax igual a Tmin es válido; los valores vacíos no se juzgan.
    Espera `date` ya normalizada. No modifica la tabla.
    """
    minimo, maximo = rango_fisico
    fuera = []  # (fecha, columna, valor), en el orden de la tabla
    for columna in COLUMNAS_TEMPERATURA:
        valores = tabla[columna]
        for indice in tabla.index[valores.notna() & ~valores.between(minimo, maximo)]:
            fuera.append((tabla.at[indice, "date"], columna, valores[indice]))
    if fuera:
        fecha, columna, valor = min(fuera, key=lambda f: f[0])
        sustantivo = "temperatura" if len(fuera) == 1 else "temperaturas"
        raise ErrorDeEntrada(
            f"{len(fuera)} {sustantivo} fuera del rango físico ({minimo:g}, {maximo:g}) °C. "
            f"Ejemplo: {columna} = {valor:g} el {pd.Timestamp(fecha):%Y-%m-%d}."
        )

    invertidos = tabla.loc[tabla["Tmax"] < tabla["Tmin"], "date"]
    if len(invertidos):
        nombrados = ", ".join(f"{pd.Timestamp(f):%Y-%m-%d}" for f in invertidos.iloc[:MAX_FECHAS_EN_EL_ERROR])
        resto = len(invertidos) - MAX_FECHAS_EN_EL_ERROR
        mas = f" (y {resto} más)" if resto > 0 else ""
        sustantivo = "día" if len(invertidos) == 1 else "días"
        raise ErrorDeEntrada(
            f"{len(invertidos)} {sustantivo} con Tmax menor que Tmin. Primeros: {nombrados}{mas}."
        )


def preparar_clima(
    tabla: pd.DataFrame, parametros: ParametrosClima | None = None
) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Valida y normaliza la tabla diaria: todo el bloque de entrada de la spec 002 (RF-1 a RF-8).

    Devuelve `date` (día), `Tmax`, `Tmin` (decimales) y `disponible` (verdadero si el día tiene las
    dos temperaturas), ordenada por fecha y con índice nuevo, más las advertencias de la entrada.
    Un día con una temperatura vacía queda en la tabla como faltante (RF-7); las columnas extra
    se ignoran y no pasan al resultado (RF-8). No modifica la tabla de entrada.
    """
    parametros = parametros or ParametrosClima()
    validar_columnas_y_temperaturas(tabla)

    base = pd.DataFrame(
        {
            "date": normalizar_fechas(tabla["date"], parametros.formato_fecha),
            "Tmax": pd.to_numeric(tabla["Tmax"]).astype(float),
            "Tmin": pd.to_numeric(tabla["Tmin"]).astype(float),
        }
    )
    base, advertencias = descartar_fechas_duplicadas(base)
    validar_temperaturas_plausibles(base, parametros.rango_fisico)

    base = base.sort_values("date", kind="stable").reset_index(drop=True)
    base["disponible"] = base["Tmax"].notna() & base["Tmin"].notna()
    return base, advertencias
