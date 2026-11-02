"""T4.1: validación de la serie de KVPI (RF-1 a RF-6 de la spec 004)."""

import io

import numpy as np
import pandas as pd
import pytest

from kiwitracking.kvpi import validar_serie
from kiwitracking.resultado import ErrorDeEntrada


def _serie(filas, columnas=("id", "campaña", "KVPI")):
    return pd.DataFrame(filas, columns=list(columnas))


def _csv(texto):
    """Lee un CSV como lo hace el programa, para probar los textos que `pandas` toma como vacíos."""
    return pd.read_csv(io.StringIO(texto))


BASE = [(1, "2019_2020", 0.4), (1, "2020_2021", 0.5), (2, "2019_2020", 0.3), (2, "2020_2021", 0.6)]


def test_rf1_serie_valida_devuelve_id_campana_y_kvpi():
    tabla, avisos = validar_serie(_serie(BASE))
    assert list(tabla.columns) == ["id", "campana", "KVPI"]
    assert len(tabla) == 4
    assert avisos == []


def test_rf1_acepta_campana_sin_enie():
    tabla, _ = validar_serie(_serie(BASE, ("id", "campana", "KVPI")))
    assert list(tabla["campana"].unique()) == ["2019_2020", "2020_2021"]


@pytest.mark.parametrize(
    "columnas, nombrada",
    [
        (("campaña", "KVPI"), "id"),
        (("id", "campaña"), "KVPI"),
        (("id", "KVPI"), "campaña"),
    ],
)
def test_rf1_falta_una_columna_obligatoria_y_la_nombra(columnas, nombrada):
    serie = pd.DataFrame({columna: [1.0] for columna in columnas})
    with pytest.raises(ErrorDeEntrada, match=nombrada):
        validar_serie(serie)


def test_rf1_faltan_varias_columnas_las_nombra_todas():
    with pytest.raises(ErrorDeEntrada) as error:
        validar_serie(pd.DataFrame({"x": [1]}))
    for nombre in ("id", "KVPI", "campaña"):
        assert nombre in str(error.value)


def test_rf1_serie_vacia_es_un_error():
    with pytest.raises(ErrorDeEntrada, match="vac"):
        validar_serie(pd.DataFrame(columns=["id", "campaña", "KVPI"]))


def test_rf1_campana_y_campana_a_la_vez_piden_indicar_una():
    serie = pd.DataFrame({"id": [1], "campaña": ["a"], "campana": ["a"], "KVPI": [0.1]})
    with pytest.raises(ErrorDeEntrada, match="una sola"):
        validar_serie(serie)


def test_rf2_ids_vacios_dan_error_con_la_cantidad():
    serie = _serie([(1, "a", 0.1), (None, "a", 0.2), ("  ", "b", 0.3)])
    with pytest.raises(ErrorDeEntrada, match="2 filas"):
        validar_serie(serie)


def test_rf2_campanas_vacias_dan_error_con_la_cantidad():
    serie = _serie([(1, "a", 0.1), (2, None, 0.2), (3, "", 0.3), (4, "   ", 0.4)])
    with pytest.raises(ErrorDeEntrada, match="3 filas"):
        validar_serie(serie)


def test_rf2_una_fila_usa_el_singular():
    with pytest.raises(ErrorDeEntrada, match="1 fila "):
        validar_serie(_serie([(1, "a", 0.1), (None, "a", 0.2)]))


def test_rf3_texto_no_numerico_da_error_con_la_columna_y_un_ejemplo():
    with pytest.raises(ErrorDeEntrada, match="KVPI") as error:
        validar_serie(_serie([(1, "a", 0.1), (2, "a", "n/d")]))
    assert "n/d" in str(error.value)


def test_rf3_guion_tambien_es_texto_no_numerico():
    with pytest.raises(ErrorDeEntrada, match="'-'"):
        validar_serie(_serie([(1, "a", 0.1), (2, "a", "-")]))


def test_rf3_coma_decimal_se_menciona_como_causa_probable():
    serie = _csv('id,campaña,KVPI\n1,a,"0,41"\n2,a,"0,52"\n')
    with pytest.raises(ErrorDeEntrada, match="coma decimal"):
        validar_serie(serie)


def test_rf3_texto_sin_coma_no_menciona_la_coma():
    with pytest.raises(ErrorDeEntrada) as error:
        validar_serie(_serie([(1, "a", 0.1), (2, "a", "n/d")]))
    assert "coma" not in str(error.value)


@pytest.mark.parametrize("infinito", [np.inf, -np.inf])
def test_rf3_infinitos_dan_error_con_la_cantidad(infinito):
    serie = _serie([(1, "a", 0.1), (2, "a", infinito), (3, "a", infinito)])
    with pytest.raises(ErrorDeEntrada, match="2 valores infinitos"):
        validar_serie(serie)


def test_rf3_el_texto_inf_tambien_cuenta_como_infinito():
    with pytest.raises(ErrorDeEntrada, match="infinito"):
        validar_serie(_csv("id,campaña,KVPI\n1,a,inf\n2,a,0.2\n"))


def test_rf3_celda_en_blanco_es_una_campana_sin_dato_y_no_un_error():
    tabla, avisos = validar_serie(_csv("id,campaña,KVPI\n1,a,0.1\n1,b,\n"))
    assert len(tabla) == 2
    assert tabla["KVPI"].isna().sum() == 1
    assert avisos == []


@pytest.mark.parametrize("texto", ["NA", "NaN", "null", "N/A"])
def test_rf3_textos_ausentes_de_pandas_son_vacios_sin_aviso(texto):
    tabla, avisos = validar_serie(_csv(f"id,campaña,KVPI\n1,a,0.1\n1,b,{texto}\n"))
    assert tabla["KVPI"].isna().sum() == 1
    assert avisos == []


def test_rf4_repetidos_iguales_se_unifican_con_aviso():
    serie = _serie(BASE + [(1, "2019_2020", 0.4), (2, "2020_2021", 0.6)])
    tabla, avisos = validar_serie(serie)
    assert len(tabla) == 4
    assert [a.codigo for a in avisos] == ["KVPI_DUPLICADO"]
    assert "2" in avisos[0].mensaje


def test_rf4_dos_repetidos_vacios_son_iguales_y_se_unifican():
    serie = _serie([(1, "a", None), (1, "a", None), (1, "b", 0.2)])
    tabla, avisos = validar_serie(serie)
    assert len(tabla) == 2
    assert [a.codigo for a in avisos] == ["KVPI_DUPLICADO"]


def test_rf4_repetidos_con_valores_distintos_dan_error_con_el_par():
    serie = _serie(BASE + [(2, "2020_2021", 0.7)])
    with pytest.raises(ErrorDeEntrada) as error:
        validar_serie(serie)
    assert "2" in str(error.value) and "2020_2021" in str(error.value)


def test_rf4_un_numero_contra_un_vacio_es_un_conflicto():
    serie = _serie([(1, "a", 0.4), (1, "a", None)])
    with pytest.raises(ErrorDeEntrada, match="distintos"):
        validar_serie(serie)


def test_rf4_el_error_nombra_hasta_10_pares_y_cuantos_mas_hay():
    filas = []
    for planta in range(13):
        filas += [(planta, "a", 0.1), (planta, "a", 0.2)]
    with pytest.raises(ErrorDeEntrada) as error:
        validar_serie(_serie(filas))
    texto = str(error.value)
    assert "13" in texto
    assert "3 más" in texto
    assert texto.count("/a") == 10


def test_rf4_con_exactamente_10_pares_no_dice_cuantos_mas_hay():
    filas = []
    for planta in range(10):
        filas += [(planta, "a", 0.1), (planta, "a", 0.2)]
    with pytest.raises(ErrorDeEntrada) as error:
        validar_serie(_serie(filas))
    assert "más" not in str(error.value)


def test_rf4_tres_filas_iguales_cuentan_dos_descartadas():
    serie = _serie([(1, "a", 0.4)] * 3 + [(1, "b", 0.5)])
    tabla, avisos = validar_serie(serie)
    assert len(tabla) == 2
    assert "2" in avisos[0].mensaje


def test_rf5_etiquetas_con_espacios_son_la_misma_campana():
    serie = _serie([(1, "2019_2020", 0.4), (1, "2019_2020 ", 0.4), (2, " 2019_2020", 0.3)])
    tabla, avisos = validar_serie(serie)
    assert list(tabla["campana"].unique()) == ["2019_2020"]
    assert [a.codigo for a in avisos] == ["KVPI_DUPLICADO"]


def test_rf5_etiquetas_con_espacios_y_valores_distintos_son_un_conflicto():
    serie = _serie([(1, "2019_2020", 0.4), (1, "2019_2020 ", 0.5)])
    with pytest.raises(ErrorDeEntrada):
        validar_serie(serie)


def test_rf5_no_interpreta_ni_unifica_formatos_distintos():
    serie = _serie([(1, "2019_2020", 0.4), (1, "2019-2020", 0.5)])
    tabla, _ = validar_serie(serie)
    assert sorted(tabla["campana"].unique()) == ["2019-2020", "2019_2020"]


def test_rf5_las_etiquetas_numericas_se_leen_como_texto():
    tabla, _ = validar_serie(_serie([(1, 2019, 0.4), (1, 2020, 0.5)]))
    assert sorted(tabla["campana"].unique()) == ["2019", "2020"]


def test_rf6_el_resultado_no_depende_del_orden_de_las_filas():
    serie = _serie(BASE + [(3, "2019_2020", 0.123456789), (3, "2020_2021", 0.987654321)])
    esperado, _ = validar_serie(serie)
    for semilla in range(5):
        barajada = serie.sample(frac=1, random_state=semilla).reset_index(drop=True)
        obtenido, _ = validar_serie(barajada)
        pd.testing.assert_frame_equal(obtenido.reset_index(drop=True), esperado.reset_index(drop=True))


def test_rf6_las_columnas_extra_y_su_orden_no_cambian_el_resultado():
    base = _serie(BASE)
    con_extra = base.assign(row=1, col=2, geo="x")[["geo", "KVPI", "row", "campaña", "id", "col"]]
    sin_extra, _ = validar_serie(base)
    con, _ = validar_serie(con_extra)
    pd.testing.assert_frame_equal(sin_extra.reset_index(drop=True), con.reset_index(drop=True))


def test_rf6_no_modifica_la_tabla_de_entrada():
    serie = _serie(BASE + [(1, "2019_2020 ", 0.4)])
    copia = serie.copy()
    validar_serie(serie)
    pd.testing.assert_frame_equal(serie, copia)
