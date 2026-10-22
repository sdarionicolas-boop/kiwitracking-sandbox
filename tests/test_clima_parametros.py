import dataclasses

import numpy as np
import pytest

from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import ErrorDeEntrada


def test_rf9_los_valores_por_defecto_son_los_de_la_spec():
    p = ParametrosClima()

    assert p.ventana_frio == "invierno"
    assert p.tbase == 10
    assert p.umbral_frio == 7
    assert p.meses_frio == (5, 6, 7, 8)
    assert p.mes_inicio_temporada == 7
    assert p.cobertura_minima == 0.9
    assert p.max_hueco_dias == 7
    assert p.umbral_optimo == 950
    assert p.umbral_adecuado == 750
    assert p.rango_fisico == (-60, 60)
    assert p.campana is None
    assert p.formato_fecha is None


def test_rf9_los_parametros_son_inmutables():
    p = ParametrosClima()

    with pytest.raises(dataclasses.FrozenInstanceError):
        p.tbase = 5


@pytest.mark.parametrize("valor", ["invierno", "temporada"])
def test_rf9_ventana_frio_permitida_no_da_error(valor):
    assert ParametrosClima(ventana_frio=valor).ventana_frio == valor


@pytest.mark.parametrize("valor", ["Invierno", "otoño", "", None, 1])
def test_rf9_ventana_frio_no_permitida_da_error_que_nombra_los_valores_permitidos(valor):
    with pytest.raises(ErrorDeEntrada) as error:
        ParametrosClima(ventana_frio=valor)

    assert "invierno" in str(error.value) and "temporada" in str(error.value)


@pytest.mark.parametrize("valor", [0, 0.9, 1, 1.0])
def test_rf9_cobertura_minima_entre_0_y_1_no_da_error(valor):
    ParametrosClima(cobertura_minima=valor)


@pytest.mark.parametrize("valor", [-0.1, 1.1, 90, "0.9", None, True])
def test_rf9_cobertura_minima_fuera_de_0_y_1_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="cobertura_minima.*0 y 1"):
        ParametrosClima(cobertura_minima=valor)


@pytest.mark.parametrize("valor", [None, 0, 7, np.int64(10)])
def test_rf9_max_hueco_dias_none_o_entero_no_negativo_no_da_error(valor):
    ParametrosClima(max_hueco_dias=valor)


@pytest.mark.parametrize("valor", [-1, 7.5, "7", True])
def test_rf9_max_hueco_dias_negativo_o_no_entero_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="max_hueco_dias"):
        ParametrosClima(max_hueco_dias=valor)


def test_rf9_umbral_optimo_mayor_que_umbral_adecuado_no_da_error():
    ParametrosClima(umbral_optimo=1000, umbral_adecuado=500)


@pytest.mark.parametrize("optimo,adecuado", [(750, 750), (700, 750)])
def test_rf9_umbral_optimo_menor_o_igual_que_umbral_adecuado_da_error_que_nombra_los_dos(optimo, adecuado):
    with pytest.raises(ErrorDeEntrada) as error:
        ParametrosClima(umbral_optimo=optimo, umbral_adecuado=adecuado)

    assert "umbral_optimo" in str(error.value) and "umbral_adecuado" in str(error.value)


def test_rf9_rango_fisico_con_minimo_menor_que_maximo_no_da_error():
    ParametrosClima(rango_fisico=(-30, 55))


@pytest.mark.parametrize("valor", [(10, 10), (60, -60), (1,), (1, 2, 3), "ab", None])
def test_rf9_rango_fisico_invalido_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="rango_fisico"):
        ParametrosClima(rango_fisico=valor)


@pytest.mark.parametrize("valor", [1, 7, 12])
def test_rf9_mes_inicio_temporada_de_1_a_12_no_da_error(valor):
    ParametrosClima(mes_inicio_temporada=valor)


@pytest.mark.parametrize("valor", [0, 13, 7.5, "7", None])
def test_rf9_mes_inicio_temporada_fuera_de_1_a_12_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="mes_inicio_temporada.*1 y 12"):
        ParametrosClima(mes_inicio_temporada=valor)


@pytest.mark.parametrize("meses", [(5, 6, 7, 8), (5,), (6, 7), (1, 2, 3), (8, 7, 6, 5)])
def test_rf9_en_modo_invierno_una_serie_continua_dentro_del_ano_no_da_error(meses):
    ParametrosClima(ventana_frio="invierno", meses_frio=meses)


@pytest.mark.parametrize("meses", [(11, 12, 1, 2), (12, 1), (5, 7, 8), (1, 12)])
def test_rf9_en_modo_invierno_una_ventana_que_cruza_el_fin_de_ano_o_tiene_saltos_da_error_que_lo_explica(meses):
    with pytest.raises(ErrorDeEntrada) as error:
        ParametrosClima(ventana_frio="invierno", meses_frio=meses)

    texto = str(error.value)
    assert "fin de año" in texto and "continuas" in texto and "año calendario" in texto


@pytest.mark.parametrize("meses", [(11, 12, 1, 2), (5, 7, 8)])
def test_rf9_en_modo_temporada_esas_mismas_ventanas_se_aceptan(meses):
    ParametrosClima(ventana_frio="temporada", meses_frio=meses)


@pytest.mark.parametrize("ventana", ["invierno", "temporada"])
@pytest.mark.parametrize("meses", [(), (0, 5), (13,), (5.5,), ("mayo",), None])
def test_rf9_meses_frio_vacio_o_con_meses_fuera_de_1_a_12_da_error_en_cualquier_modo(ventana, meses):
    with pytest.raises(ErrorDeEntrada, match="meses_frio"):
        ParametrosClima(ventana_frio=ventana, meses_frio=meses)


@pytest.mark.parametrize("valor", [None, 2024, np.int64(2024)])
def test_rf9_campana_none_o_entera_no_da_error(valor):
    ParametrosClima(campana=valor)


@pytest.mark.parametrize("valor", ["2024", 2024.5, True])
def test_rf9_campana_que_no_es_entera_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="campana"):
        ParametrosClima(campana=valor)


@pytest.mark.parametrize("valor", [None, "%d/%m/%Y", "%Y-%m-%d"])
def test_rf9_formato_fecha_none_o_texto_no_da_error(valor):
    ParametrosClima(formato_fecha=valor)


@pytest.mark.parametrize("valor", [5, "", ["%d/%m/%Y"]])
def test_rf9_formato_fecha_que_no_es_texto_da_error(valor):
    with pytest.raises(ErrorDeEntrada, match="formato_fecha"):
        ParametrosClima(formato_fecha=valor)


def test_rf9_los_valores_normales_se_guardan_como_se_pasaron():
    p = ParametrosClima(ventana_frio="temporada", tbase=12.5, cobertura_minima=0.8, max_hueco_dias=None, campana=2023)

    assert (p.ventana_frio, p.tbase, p.cobertura_minima, p.max_hueco_dias, p.campana) == ("temporada", 12.5, 0.8, None, 2023)
