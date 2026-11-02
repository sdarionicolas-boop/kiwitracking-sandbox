"""Días estimados del clima (spec 005): parámetro, entrada y recuento por ventana (RF-1 a RF-5 y RF-9)."""

import numpy as np
import pandas as pd
import pytest

from kiwitracking.clima_entrada import preparar_clima, preparar_clima_con_origen
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import ErrorDeEntrada

# --- T5.0: el parámetro `origenes_estimados` (RF-9) ------------------------------------------------------------


def test_rf9_el_valor_por_defecto_es_interpolado():
    assert ParametrosClima().origenes_estimados == ("interpolado",)


def test_rf9_una_lista_se_convierte_en_tupla():
    parametros = ParametrosClima(origenes_estimados=["interpolado", "estimado"])
    assert parametros.origenes_estimados == ("interpolado", "estimado")
    assert isinstance(parametros.origenes_estimados, tuple)


def test_rf9_acepta_una_tupla_de_un_solo_elemento():
    assert ParametrosClima(origenes_estimados=("satelital",)).origenes_estimados == ("satelital",)


@pytest.mark.parametrize(
    "valor",
    [
        [],
        (),
        "interpolado",
        None,
        3,
        {"interpolado"},
        [""],
        ["   "],
        ["interpolado", ""],
        ["interpolado", None],
        ["interpolado", 3],
        [np.nan],
    ],
)
def test_rf9_un_valor_no_permitido_da_error_con_lo_que_se_espera(valor):
    with pytest.raises(ErrorDeEntrada, match="origenes_estimados") as error:
        ParametrosClima(origenes_estimados=valor)
    assert "lista" in str(error.value) and "textos" in str(error.value)


def test_rf9_los_demas_parametros_no_cambian():
    parametros = ParametrosClima()
    assert (parametros.ventana_frio, parametros.cobertura_minima, parametros.max_hueco_dias) == ("invierno", 0.9, 7)
    assert parametros.umbral_optimo == 950 and parametros.meses_frio == (5, 6, 7, 8)


# --- T5.1: preparar el clima con `origen` (RF-3, RF-4, RF-5) -----------------------------------------------------

def _clima(filas, columnas=("date", "Tmax", "Tmin", "origen")):
    return pd.DataFrame(filas, columns=list(columnas))


FILAS = [
    ("2024-05-01", 15.0, 5.0, "INTA_verificado"),
    ("2024-05-02", 16.0, 6.0, "interpolado"),
    ("2024-05-03", 14.0, 4.0, "INTA_verificado"),
    ("2024-05-04", 13.0, 3.0, "interpolado"),
]


def test_rf1_la_tabla_trae_la_columna_estimado_como_booleana():
    tabla, _ = preparar_clima_con_origen(_clima(FILAS))
    assert list(tabla.columns) == ["date", "Tmax", "Tmin", "disponible", "estimado"]
    assert tabla["estimado"].dtype == bool
    assert tabla["estimado"].tolist() == [False, True, False, True]


@pytest.mark.parametrize("etiqueta", ["Interpolado", "INTERPOLADO", "  interpolado  ", "\tinterpolado\n"])
def test_rf1_la_etiqueta_se_compara_sin_espacios_y_sin_distinguir_mayusculas(etiqueta):
    tabla, _ = preparar_clima_con_origen(_clima([("2024-05-01", 15.0, 5.0, etiqueta)]))
    assert tabla["estimado"].tolist() == [True]


@pytest.mark.parametrize("etiqueta", [None, np.nan, "", "   ", "medido", "interpolada", 0, 1, 1.0, True])
def test_rf1_una_celda_vacia_una_etiqueta_numerica_o_ajena_a_la_lista_no_es_estimada(etiqueta):
    tabla, _ = preparar_clima_con_origen(_clima([("2024-05-01", 15.0, 5.0, etiqueta)]))
    assert tabla["estimado"].tolist() == [False]


def test_rf1_la_lista_de_etiquetas_es_un_parametro():
    parametros = ParametrosClima(origenes_estimados=[" Satelital", "estimado"])
    filas = [("2024-05-01", 15.0, 5.0, "satelital"), ("2024-05-02", 15.0, 5.0, "ESTIMADO"),
             ("2024-05-03", 15.0, 5.0, "interpolado")]  # fmt: skip
    tabla, _ = preparar_clima_con_origen(_clima(filas), parametros)
    assert tabla["estimado"].tolist() == [True, True, False]


def test_rf1_una_columna_origen_completamente_vacia_da_todo_falso():
    filas = [("2024-05-01", 15.0, 5.0, None), ("2024-05-02", 15.0, 5.0, np.nan)]
    tabla, _ = preparar_clima_con_origen(_clima(filas))
    assert tabla["estimado"].tolist() == [False, False]


def test_rf2_sin_la_columna_origen_no_hay_columna_estimado():
    tabla, avisos = preparar_clima_con_origen(_clima(FILAS, ("date", "Tmax", "Tmin", "otra")))
    assert list(tabla.columns) == ["date", "Tmax", "Tmin", "disponible"]
    assert avisos == []


def test_rf3_un_dia_sin_temperaturas_no_es_estimado_aunque_tenga_la_etiqueta():
    filas = [("2024-05-01", np.nan, 5.0, "interpolado"), ("2024-05-02", 15.0, np.nan, "interpolado"),
             ("2024-05-03", np.nan, np.nan, "interpolado"), ("2024-05-04", 15.0, 5.0, "interpolado")]  # fmt: skip
    tabla, _ = preparar_clima_con_origen(_clima(filas))
    assert tabla["disponible"].tolist() == [False, False, False, True]
    assert tabla["estimado"].tolist() == [False, False, False, True]


def test_rf4_con_una_fecha_repetida_se_usa_el_origen_de_la_primera_aparicion():
    filas = [("2024-05-01", 15.0, 5.0, "interpolado"), ("2024-05-01", 15.0, 5.0, "INTA_verificado"),
             ("2024-05-02", 16.0, 6.0, "INTA_verificado"), ("2024-05-02", 16.0, 6.0, "interpolado")]  # fmt: skip
    tabla, avisos = preparar_clima_con_origen(_clima(filas))
    assert tabla["date"].tolist() == list(pd.to_datetime(["2024-05-01", "2024-05-02"]))
    assert tabla["estimado"].tolist() == [True, False]
    assert [a.codigo for a in avisos] == ["FECHA_DUPLICADA"]


def test_rf4_la_regla_vale_aunque_la_primera_fila_no_sea_la_primera_del_orden_cronologico():
    filas = [("2024-05-02", 16.0, 6.0, "interpolado"), ("2024-05-01", 15.0, 5.0, "INTA_verificado"),
             ("2024-05-02", 16.0, 6.0, "INTA_verificado")]  # fmt: skip
    tabla, _ = preparar_clima_con_origen(_clima(filas))
    assert tabla["estimado"].tolist() == [False, True]  # el 02 se vio primero con "interpolado"


def test_rf5_el_resultado_no_depende_del_orden_de_las_filas_cuando_no_hay_repetidas():
    esperado, _ = preparar_clima_con_origen(_clima(FILAS))
    for semilla in range(5):
        barajada = _clima(FILAS).sample(frac=1, random_state=semilla).reset_index(drop=True)
        obtenido, _ = preparar_clima_con_origen(barajada)
        pd.testing.assert_frame_equal(obtenido, esperado)


def test_rf5_las_columnas_extra_y_su_orden_no_cambian_el_resultado():
    esperado, _ = preparar_clima_con_origen(_clima(FILAS))
    con_extra = _clima(FILAS).assign(nota="x", otra=3)[["nota", "origen", "Tmin", "otra", "Tmax", "date"]]
    obtenido, _ = preparar_clima_con_origen(con_extra)
    pd.testing.assert_frame_equal(obtenido, esperado)


def test_no_modifica_la_tabla_de_entrada():
    entrada = _clima(FILAS + [("2024-05-04", 13.0, 3.0, "interpolado")])
    copia = entrada.copy()
    preparar_clima_con_origen(entrada)
    pd.testing.assert_frame_equal(entrada, copia)


def test_rf2_preparar_clima_devuelve_lo_de_antes_con_o_sin_la_columna_origen():
    con_origen, avisos_con = preparar_clima(_clima(FILAS))
    sin_origen, avisos_sin = preparar_clima(_clima(FILAS).drop(columns="origen"))
    assert list(con_origen.columns) == ["date", "Tmax", "Tmin", "disponible"]
    pd.testing.assert_frame_equal(con_origen, sin_origen)
    assert avisos_con == avisos_sin == []


def test_los_errores_de_validacion_del_clima_siguen_igual_con_origen():
    filas = [("2024-05-01", 15.0, 5.0, "interpolado"), ("2024-05-01", 16.0, 5.0, "interpolado")]
    with pytest.raises(ErrorDeEntrada, match="distintas"):
        preparar_clima_con_origen(_clima(filas))
