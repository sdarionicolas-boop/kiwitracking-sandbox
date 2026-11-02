"""T4.4: cobertura por campaña y lista de campañas esperadas (RF-20 a RF-22 de la spec 004)."""

import numpy as np
import pandas as pd
import pytest

from kiwitracking.kvpi import CoberturaCampana, agregar_kvpi
from kiwitracking.resultado import ErrorDeEntrada

NAN = None


def _serie(filas):
    return pd.DataFrame(filas, columns=["id", "campaña", "KVPI"])


# Cuatro plantas. c1: las 4 con dato. c2: 2 de 4. c3: 1 de 4. c4: ninguna (la campaña existe, con todo vacío).
SERIE = _serie(
    [
        (1, "c1", 0.1), (1, "c2", 0.2), (1, "c3", 0.3), (1, "c4", NAN),
        (2, "c1", 0.1), (2, "c2", 0.2), (2, "c3", NAN), (2, "c4", NAN),
        (3, "c1", 0.1), (3, "c2", NAN), (3, "c3", NAN), (3, "c4", NAN),
        (4, "c1", 0.1), (4, "c2", NAN), (4, "c3", NAN), (4, "c4", NAN),
    ]
)  # fmt: skip


def _cobertura(resultado):
    return {c.campana: c for c in resultado.cobertura}


def test_rf20_cobertura_por_campana_en_orden_de_etiqueta():
    resultado = agregar_kvpi(SERIE)
    assert [c.campana for c in resultado.cobertura] == ["c1", "c2", "c3", "c4"]
    assert all(isinstance(c, CoberturaCampana) for c in resultado.cobertura)


def test_rf20_cuenta_plantas_con_dato_y_proporcion_sobre_las_plantas_de_la_serie():
    cobertura = _cobertura(agregar_kvpi(SERIE))
    assert [cobertura[c].plantas_con_dato for c in ("c1", "c2", "c3", "c4")] == [4, 2, 1, 0]
    assert [cobertura[c].proporcion for c in ("c1", "c2", "c3", "c4")] == [1.0, 0.5, 0.25, 0.0]


def test_rf20_una_campana_sin_ninguna_planta_con_dato_figura_con_cero():
    assert _cobertura(agregar_kvpi(SERIE))["c4"].plantas_con_dato == 0


def test_rf20_una_fila_con_kvpi_vacio_no_es_una_planta_con_dato():
    serie = _serie([(1, "c1", 0.1), (2, "c1", NAN)])
    assert _cobertura(agregar_kvpi(serie))["c1"].plantas_con_dato == 1


def test_rf20_las_plantas_de_referencia_se_pueden_indicar():
    cobertura = _cobertura(agregar_kvpi(SERIE, total_plantas=8))
    assert cobertura["c1"].proporcion == 0.5
    assert cobertura["c3"].proporcion == 0.125


def test_rf20_las_plantas_de_referencia_incluyen_las_que_no_tienen_ningun_dato():
    serie = _serie([(1, "c1", 0.1), (2, "c1", NAN)])
    assert _cobertura(agregar_kvpi(serie))["c1"].proporcion == 0.5


@pytest.mark.parametrize("valor", [0, -1, 2.5, "3", True])
def test_rf20_total_plantas_no_permitido_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="total_plantas"):
        agregar_kvpi(SERIE, total_plantas=valor)


def test_rf21_una_campana_por_debajo_del_minimo_avisa_con_nombre_cantidad_y_proporcion():
    resultado = agregar_kvpi(SERIE)
    avisos = [a for a in resultado.advertencias if a.codigo == "CAMPANA_CON_POCOS_DATOS"]
    assert len(avisos) == 2  # c3 (25 %) y c4 (0 %); c2 está justo en el mínimo
    assert "c3" in avisos[0].mensaje and "1 de 4" in avisos[0].mensaje and "25,0 %" in avisos[0].mensaje
    assert "c4" in avisos[1].mensaje and "0 de 4" in avisos[1].mensaje and "0,0 %" in avisos[1].mensaje


def test_rf21_justo_en_el_minimo_no_avisa():
    resultado = agregar_kvpi(SERIE)
    assert not any("c2" in a.mensaje for a in resultado.advertencias if a.codigo == "CAMPANA_CON_POCOS_DATOS")


def test_rf21_el_minimo_es_un_parametro():
    def avisos(minimo):
        resultado = agregar_kvpi(SERIE, cobertura_minima_campana=minimo)
        return [a for a in resultado.advertencias if a.codigo == "CAMPANA_CON_POCOS_DATOS"]

    assert avisos(0) == []
    assert len(avisos(0.1)) == 1  # solo c4 (0,0)
    assert len(avisos(0.3)) == 2  # c3 (0,25) y c4
    assert len(avisos(1)) == 3


def test_rf21_con_cobertura_completa_no_avisa():
    serie = _serie([(1, "c1", 0.1), (1, "c2", 0.2), (2, "c1", 0.1), (2, "c2", 0.2)])
    assert agregar_kvpi(serie).advertencias == []


@pytest.mark.parametrize("valor", [-0.1, 1.1, np.nan, np.inf, "0.5", None, True])
def test_rf21_minimo_fuera_de_0_a_1_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="entre 0 y 1"):
        agregar_kvpi(SERIE, cobertura_minima_campana=valor)


@pytest.mark.parametrize("valor", [0, 1, 0.5, np.float64(0.2)])
def test_rf21_acepta_numeros_de_0_a_1(valor):
    agregar_kvpi(SERIE, cobertura_minima_campana=valor)


def test_rf21_los_avisos_de_cobertura_van_despues_de_los_de_planta():
    codigos = [a.codigo for a in agregar_kvpi(SERIE).advertencias]
    assert codigos == ["PLANTAS_CON_MENOS_CAMPANAS", "SIN_DESVIO", "CAMPANA_CON_POCOS_DATOS", "CAMPANA_CON_POCOS_DATOS"]


def test_rf22_con_las_campanas_esperadas_correctas_no_da_error():
    resultado = agregar_kvpi(SERIE, campanas=["c1", "c2", "c3", "c4"])
    assert [c.campana for c in resultado.cobertura] == ["c1", "c2", "c3", "c4"]


def test_rf22_el_orden_y_el_tipo_de_la_lista_no_importan():
    agregar_kvpi(SERIE, campanas=("c4", "c3", "c2", "c1"))


def test_rf22_las_etiquetas_esperadas_se_comparan_sin_espacios_al_inicio_ni_al_final():
    agregar_kvpi(SERIE, campanas=[" c1", "c2 ", "c3", "c4"])


def test_rf22_una_esperada_que_no_esta_en_la_serie_da_error_que_la_nombra():
    with pytest.raises(ErrorDeEntrada, match="2019_2020") as error:
        agregar_kvpi(SERIE, campanas=["c1", "c2", "c3", "c4", "2019_2020"])
    assert "no aparecen en la serie" in str(error.value)


def test_rf22_una_encontrada_que_no_estaba_entre_las_esperadas_da_error_que_la_nombra():
    with pytest.raises(ErrorDeEntrada, match="c4") as error:
        agregar_kvpi(SERIE, campanas=["c1", "c2", "c3"])
    assert "no estaban entre las esperadas" in str(error.value)


def test_rf22_con_faltante_y_sobrante_el_error_nombra_las_dos():
    with pytest.raises(ErrorDeEntrada) as error:
        agregar_kvpi(SERIE, campanas=["c1", "c2", "c3", "x9"])
    assert "x9" in str(error.value) and "c4" in str(error.value)


def test_rf22_lista_vacia_da_error():
    with pytest.raises(ErrorDeEntrada, match="vacía"):
        agregar_kvpi(SERIE, campanas=[])


def test_rf22_etiqueta_repetida_da_error():
    with pytest.raises(ErrorDeEntrada, match="repite"):
        agregar_kvpi(SERIE, campanas=["c1", "c2", "c3", "c4", "c1"])


def test_rf22_repetida_solo_por_espacios_da_error():
    with pytest.raises(ErrorDeEntrada, match="repite"):
        agregar_kvpi(SERIE, campanas=["c1", "c1 ", "c2", "c3", "c4"])


def test_rf22_un_texto_en_vez_de_una_lista_da_error():
    with pytest.raises(ErrorDeEntrada, match="no un solo texto"):
        agregar_kvpi(SERIE, campanas="c1,c2,c3,c4")


def test_rf22_sin_lista_una_campana_que_falta_por_completo_no_se_detecta():
    serie = _serie([(1, "c1", 0.1), (1, "c2", 0.2), (2, "c1", 0.1), (2, "c2", 0.2)])
    resultado = agregar_kvpi(serie)  # falta c3 en toda la serie: no hay manera de saberlo
    assert [c.campana for c in resultado.cobertura] == ["c1", "c2"]
    assert resultado.advertencias == []


def test_la_cobertura_no_cambia_el_resultado_por_planta():
    con = agregar_kvpi(SERIE, campanas=["c1", "c2", "c3", "c4"], cobertura_minima_campana=1, total_plantas=4)
    pd.testing.assert_frame_equal(con.tabla, agregar_kvpi(SERIE).tabla)


def test_rf22_una_etiqueta_esperada_vacia_da_error():
    with pytest.raises(ErrorDeEntrada, match="vacía"):
        agregar_kvpi(SERIE, campanas=["c1", "c2", "c3", "c4", "  "])
