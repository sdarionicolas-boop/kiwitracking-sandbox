"""Validación de la tabla de entrada."""

import pandas as pd

from kiwitracking.resultado import Advertencia, ErrorDeEntrada

COLUMNAS_OBLIGATORIAS = ("KVPI_mean", "KVPI_std", "bajo_malla")
MODOS_CORRECCION = ("auto", "forzar", "desactivar")
ESTADOS_FRIO = ("Deficiente", "Adecuado", "Óptimo")
PRUEBAS_T = ("welch", "student")


def validar_parametros(
    correccion: str = "auto", estado_frio_ultima_campana: str | None = None, prueba_t: str = "welch"
) -> None:
    """Detiene el análisis con ErrorDeEntrada si un parámetro tiene un valor no permitido."""
    if correccion not in MODOS_CORRECCION:
        raise ErrorDeEntrada(
            f"correccion={correccion!r} no es válido. Valores permitidos: {', '.join(MODOS_CORRECCION)}."
        )
    if prueba_t not in PRUEBAS_T:
        raise ErrorDeEntrada(f"prueba_t={prueba_t!r} no es válido. Valores permitidos: {', '.join(PRUEBAS_T)}.")
    if estado_frio_ultima_campana is not None and estado_frio_ultima_campana not in ESTADOS_FRIO:
        raise ErrorDeEntrada(
            f"estado_frio_ultima_campana={estado_frio_ultima_campana!r} no es válido. "
            f"Valores permitidos: {', '.join(ESTADOS_FRIO)}."
        )


def validar_tabla(tabla: pd.DataFrame) -> None:
    """Detiene el análisis con ErrorDeEntrada si la tabla no sirve. No modifica la tabla."""
    faltantes = [columna for columna in COLUMNAS_OBLIGATORIAS if columna not in tabla.columns]
    if faltantes:
        raise ErrorDeEntrada(f"Faltan columnas obligatorias: {', '.join(faltantes)}.")

    if tabla.empty:
        raise ErrorDeEntrada("La tabla está vacía: no hay plantas para analizar.")

    if not pd.api.types.is_numeric_dtype(tabla["KVPI_mean"]):
        raise ErrorDeEntrada("La columna KVPI_mean contiene valores no numéricos.")

    if not tabla["bajo_malla"].isin([0, 1]).all():
        raise ErrorDeEntrada("La columna bajo_malla solo admite los valores 0 y 1 (sin vacíos).")


def excluir_sin_kvpi(tabla: pd.DataFrame) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Devuelve una copia sin las plantas de KVPI_mean vacío y la advertencia con cuántas fueron."""
    validas = tabla["KVPI_mean"].notna()
    cantidad = int((~validas).sum())
    if cantidad == 0:
        return tabla.copy(), []

    mensaje = f"Se excluyeron {cantidad} plantas con KVPI_mean vacío."
    return tabla[validas].copy(), [Advertencia("PLANTAS_EXCLUIDAS", mensaje)]
