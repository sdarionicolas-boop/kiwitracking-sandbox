"""Días estimados del clima (spec 005): parámetro, entrada y recuento por ventana (RF-1 a RF-5 y RF-9)."""

import numpy as np
import pandas as pd
import pytest

from kiwitracking.clima import COLUMNAS_FRIO, ResultadoClima, calcular_clima
from kiwitracking.clima_entrada import preparar_clima, preparar_clima_con_origen
from kiwitracking.clima_origen import COLUMNAS_ESTIMADOS, contar_estimados
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


# --- T5.2: recuento por ventana (RF-1, RF-2, RF-3, RF-5) ---------------------------------------------------------

def _dias(inicio, fin, origen="INTA_verificado", tmax=15.0, tmin=5.0):
    fechas = pd.date_range(inicio, fin, freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame({"date": fechas, "Tmax": tmax, "Tmin": tmin, "origen": origen})


def _invierno(anio, estimados=0, origen_estimado="interpolado"):
    """El invierno (mayo a agosto, 123 días) con los primeros `estimados` días interpolados."""
    tabla = _dias(f"{anio}-05-01", f"{anio}-08-31")
    tabla.loc[: estimados - 1, "origen"] = origen_estimado
    return tabla


def _estimados(tabla, **parametros):
    return calcular_clima(tabla, ParametrosClima(**parametros)).estimados


def test_rf1_cuenta_los_dias_estimados_y_la_proporcion_sobre_los_disponibles_de_la_ventana():
    estimados = _estimados(_invierno(2024, estimados=10))
    assert list(estimados.columns) == COLUMNAS_ESTIMADOS == ["periodo", "dias_estimados", "proporcion_estimada"]
    assert estimados["periodo"].tolist() == [2024]
    assert estimados["dias_estimados"].tolist() == [10]
    assert estimados["proporcion_estimada"].tolist() == pytest.approx([10 / 123])


def test_rf1_una_ventana_sin_dias_estimados_figura_con_cero():
    estimados = _estimados(_invierno(2024, estimados=0))
    assert estimados["dias_estimados"].tolist() == [0] and estimados["proporcion_estimada"].tolist() == [0.0]


def test_rf1_una_ventana_toda_estimada_da_proporcion_uno():
    estimados = _estimados(_invierno(2024, estimados=123))
    assert estimados["dias_estimados"].tolist() == [123] and estimados["proporcion_estimada"].tolist() == [1.0]


def test_rf1_cada_ventana_tiene_su_propio_recuento_y_salen_ordenadas_por_periodo():
    tabla = pd.concat([_invierno(2024, estimados=26), _invierno(2023, estimados=4)], ignore_index=True)
    estimados = _estimados(tabla)
    assert estimados["periodo"].tolist() == [2023, 2024]
    assert estimados["dias_estimados"].tolist() == [4, 26]


def test_rf1_con_una_ventana_incompleta_la_proporcion_es_sobre_los_dias_disponibles_y_no_sobre_los_esperados():
    tabla = _dias("2025-05-01", "2025-06-30")  # 61 de los 123 días
    tabla.loc[:4, "origen"] = "interpolado"
    estimados = _estimados(tabla)
    assert estimados["dias_estimados"].tolist() == [5]
    assert estimados["proporcion_estimada"].tolist() == pytest.approx([5 / 61])


def test_rf1_los_dias_fuera_de_los_meses_de_frio_no_cuentan():
    tabla = pd.concat([_invierno(2024, estimados=0), _dias("2024-01-01", "2024-01-31", origen="interpolado")])
    estimados = _estimados(tabla)
    assert estimados["periodo"].tolist() == [2024] and estimados["dias_estimados"].tolist() == [0]


def test_rf1_en_modo_temporada_los_dias_se_agrupan_por_temporada():
    tabla = pd.concat(
        [_dias("2023-07-15", "2023-07-15", "interpolado"), _dias("2024-05-10", "2024-05-10", "interpolado"),
         _dias("2024-07-15", "2024-07-15", "INTA_verificado")], ignore_index=True)  # fmt: skip
    estimados = _estimados(tabla, ventana_frio="temporada")
    assert estimados["periodo"].tolist() == [2023, 2024]
    assert estimados["dias_estimados"].tolist() == [2, 0]
    assert estimados["proporcion_estimada"].tolist() == [1.0, 0.0]


def test_rf1_el_recuento_usa_la_lista_de_etiquetas_del_parametro():
    tabla = _invierno(2024, estimados=7, origen_estimado="Satelital")
    assert _estimados(tabla)["dias_estimados"].tolist() == [0]
    assert _estimados(tabla, origenes_estimados=["satelital"])["dias_estimados"].tolist() == [7]


def test_rf1_hay_una_fila_por_cada_ventana_de_la_tabla_frio():
    tabla = pd.concat([_invierno(2023, 3), _invierno(2024, 5), _dias("2025-05-01", "2025-05-20")], ignore_index=True)
    resultado = calcular_clima(tabla)
    assert resultado.estimados["periodo"].tolist() == resultado.frio["periodo"].tolist() == [2023, 2024, 2025]


def test_rf1_los_tipos_de_las_columnas_son_enteros_y_decimales():
    estimados = _estimados(_invierno(2024, estimados=10))
    assert estimados["periodo"].dtype == "int64" and estimados["dias_estimados"].dtype == "int64"
    assert estimados["proporcion_estimada"].dtype == "float64"


def test_rf3_un_dia_sin_temperaturas_no_cuenta_ni_como_estimado_ni_como_disponible():
    tabla = _invierno(2024, estimados=0)
    tabla.loc[0:6, "origen"] = "interpolado"  # siete días interpolados...
    tabla.loc[0:2, "Tmax"] = np.nan  # ...tres de ellos sin temperatura máxima
    estimados = _estimados(tabla)
    assert estimados["dias_estimados"].tolist() == [4]
    assert estimados["proporcion_estimada"].tolist() == pytest.approx([4 / 120])


def test_rf2_sin_la_columna_origen_estimados_queda_sin_filas_y_con_las_columnas_y_tipos():
    resultado = calcular_clima(_invierno(2024, 10).drop(columns="origen"))
    assert resultado.estimados.empty
    assert list(resultado.estimados.columns) == COLUMNAS_ESTIMADOS
    assert resultado.estimados["periodo"].dtype == "int64" and resultado.estimados["proporcion_estimada"].dtype == "float64"


def test_rf2_con_o_sin_origen_frio_gdd_y_advertencias_son_identicos():
    con_origen = _invierno(2024, estimados=26)
    sin_origen = con_origen.drop(columns="origen")
    a, b = calcular_clima(con_origen), calcular_clima(sin_origen)
    pd.testing.assert_frame_equal(a.frio, b.frio)
    pd.testing.assert_frame_equal(a.gdd, b.gdd)
    assert a.advertencias == b.advertencias and a.ventana_frio == b.ventana_frio
    assert list(a.frio.columns) == COLUMNAS_FRIO


def test_rf2_un_resultado_armado_a_mano_sin_estimados_sigue_funcionando():
    frio = pd.DataFrame([{c: 0 for c in COLUMNAS_FRIO}])
    resultado = ResultadoClima(frio, frio, [], "invierno")
    assert resultado.estimados.empty and list(resultado.estimados.columns) == COLUMNAS_ESTIMADOS


def test_rf2_el_valor_por_defecto_de_estimados_no_se_comparte_entre_resultados():
    frio = pd.DataFrame([{c: 0 for c in COLUMNAS_FRIO}])
    primero, segundo = ResultadoClima(frio, frio, [], "invierno"), ResultadoClima(frio, frio, [], "invierno")
    assert primero.estimados is not segundo.estimados


def test_rf5_el_recuento_no_depende_del_orden_de_las_filas_ni_de_las_columnas_extra():
    tabla = pd.concat([_invierno(2023, 4), _invierno(2024, 26)], ignore_index=True)
    esperado = _estimados(tabla)
    for semilla in range(5):
        barajada = tabla.sample(frac=1, random_state=semilla).reset_index(drop=True)
        pd.testing.assert_frame_equal(_estimados(barajada), esperado)
    con_extra = tabla.assign(nota="x", otra=3)[["nota", "origen", "Tmin", "otra", "Tmax", "date"]]
    pd.testing.assert_frame_equal(_estimados(con_extra), esperado)


def test_calcular_clima_no_modifica_la_tabla_de_entrada():
    entrada = _invierno(2024, estimados=5)
    copia = entrada.copy()
    calcular_clima(entrada)
    pd.testing.assert_frame_equal(entrada, copia)


def test_contar_estimados_directo_sin_columna_estimado_devuelve_una_tabla_vacia():
    tabla = pd.DataFrame({"date": pd.to_datetime(["2024-05-01"]), "Tmax": [15.0], "Tmin": [5.0], "disponible": [True]})
    vacio = contar_estimados(tabla, ParametrosClima())
    assert vacio.empty and list(vacio.columns) == COLUMNAS_ESTIMADOS
