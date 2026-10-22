import pandas as pd
import pytest
from scipy import stats

from kiwitracking.correccion import (
    DecisionCorreccion,
    FactorMalla,
    calcular_factor,
    decidir_modo_auto,
    evaluar_confirmacion,
)
from kiwitracking.huella import huella


def _tabla(fuera, bajo):
    """Tabla mínima: `fuera` y `bajo` son listas de KVPI_mean de cada grupo."""
    kvpi = list(fuera) + list(bajo)
    return pd.DataFrame(
        {
            "id": range(1, len(kvpi) + 1),
            "KVPI_mean": kvpi,
            "KVPI_std": [0.03] * len(kvpi),
            "bajo_malla": [0] * len(fuera) + [1] * len(bajo),
        }
    )


def test_rf6_fc_es_la_media_fuera_de_malla_sobre_la_media_bajo_malla():
    # medias: fuera = 0.6, bajo = 0.5  ->  FC = 1.2 (calculable a mano)
    factor = calcular_factor(_tabla(fuera=[0.58, 0.60, 0.62], bajo=[0.48, 0.50, 0.52]))

    assert factor.fc == pytest.approx(1.2)


def test_rf6_devuelve_el_tamano_de_cada_grupo():
    factor = calcular_factor(_tabla(fuera=[0.6, 0.6, 0.6, 0.6], bajo=[0.5, 0.5, 0.5]))

    assert factor.n_fuera == 4
    assert factor.n_bajo == 3


def test_rf6_p_valor_coincide_con_un_ejemplo_calculado_a_mano():
    # [1,2,3] vs [2,3,4]: t = 1.2247 con 4 grados de libertad -> p = 0.2879
    factor = calcular_factor(_tabla(fuera=[1.0, 2.0, 3.0], bajo=[2.0, 3.0, 4.0]))

    assert factor.p_valor == pytest.approx(0.2879, abs=1e-3)


def test_rf6_usa_la_prueba_t_de_student_con_varianzas_iguales_no_la_de_welch():
    fuera = [1.0, 2.0, 3.0]
    bajo = [2.0, 4.0, 6.0, 8.0, 10.0]
    student = stats.ttest_ind(fuera, bajo, equal_var=True).pvalue
    welch = stats.ttest_ind(fuera, bajo, equal_var=False).pvalue
    assert student != pytest.approx(welch, abs=1e-3)  # el ejemplo distingue ambas pruebas

    factor = calcular_factor(_tabla(fuera=fuera, bajo=bajo))

    assert factor.p_valor == pytest.approx(student)


def test_rf6_grupos_muy_distintos_dan_p_valor_chico_y_grupos_parecidos_p_valor_alto():
    distintos = calcular_factor(_tabla(fuera=[0.59, 0.60, 0.61, 0.60], bajo=[0.44, 0.45, 0.46, 0.45]))
    parecidos = calcular_factor(_tabla(fuera=[0.50, 0.52, 0.48, 0.51], bajo=[0.51, 0.49, 0.50, 0.52]))

    assert 0 <= distintos.p_valor < 0.001
    assert 0 <= parecidos.p_valor <= 1
    assert parecidos.p_valor > 0.5


def test_rf6_sin_plantas_bajo_malla_no_hay_fc_ni_p_valor():
    factor = calcular_factor(_tabla(fuera=[0.5, 0.6, 0.7], bajo=[]))

    assert factor.n_bajo == 0
    assert factor.n_fuera == 3
    assert factor.fc is None
    assert factor.p_valor is None


def test_rf6_sin_plantas_fuera_de_malla_no_hay_fc_ni_p_valor():
    factor = calcular_factor(_tabla(fuera=[], bajo=[0.4, 0.5]))

    assert factor.n_fuera == 0
    assert factor.fc is None
    assert factor.p_valor is None


def test_rf6_con_una_sola_planta_en_un_grupo_hay_fc_pero_no_p_valor():
    factor = calcular_factor(_tabla(fuera=[0.58, 0.62], bajo=[0.50]))

    assert factor.fc == pytest.approx(1.2)
    assert factor.p_valor is None


def test_rf6_media_bajo_malla_cero_no_da_fc():
    factor = calcular_factor(_tabla(fuera=[0.5, 0.6], bajo=[-0.1, 0.1]))

    assert factor.fc is None


def test_rf6_si_los_dos_grupos_no_tienen_variacion_no_hay_p_valor():
    factor = calcular_factor(_tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5]))

    assert factor.fc == pytest.approx(1.2)
    assert factor.p_valor is None


def test_rf6_no_modifica_la_tabla_de_entrada():
    tabla = _tabla(fuera=[0.58, 0.60, 0.62], bajo=[0.48, 0.50, 0.52])
    copia = tabla.copy()

    calcular_factor(tabla)

    pd.testing.assert_frame_equal(tabla, copia)


# --- T7: confirmación visual por huella -------------------------------------------------


def test_rf8_sin_huella_confirmada_hay_advertencia_de_falta_de_confirmacion():
    tabla = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5])

    for vacia in (None, "", "   "):
        advertencia = evaluar_confirmacion(tabla, vacia)

        assert advertencia is not None
        assert advertencia.codigo == "FALTA_CONFIRMACION"


def test_rf9_huella_que_no_coincide_da_advertencia_de_huella_no_coincide():
    tabla = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5])

    advertencia = evaluar_confirmacion(tabla, "000000000000")

    assert advertencia is not None
    assert advertencia.codigo == "HUELLA_NO_COINCIDE"


def test_rf9_si_cambia_bajo_malla_despues_de_confirmar_la_confirmacion_deja_de_valer():
    confirmada = huella(_tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5]))
    modificada = _tabla(fuera=[0.6], bajo=[0.5, 0.5, 0.5])  # una planta pasó a estar bajo malla

    advertencia = evaluar_confirmacion(modificada, confirmada)

    assert advertencia.codigo == "HUELLA_NO_COINCIDE"


def test_rf8_con_la_huella_correcta_no_hay_advertencia_y_se_puede_seguir():
    tabla = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5])

    assert evaluar_confirmacion(tabla, huella(tabla)) is None


def test_rf8_tolera_espacios_alrededor_de_la_huella_pegada():
    tabla = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5])

    assert evaluar_confirmacion(tabla, f"  {huella(tabla)}\n") is None


def test_rf9_la_comparacion_distingue_mayusculas():
    tabla = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5])

    advertencia = evaluar_confirmacion(tabla, huella(tabla).upper())

    assert advertencia.codigo == "HUELLA_NO_COINCIDE"


def test_rf8_la_evaluacion_no_depende_del_modo_de_correccion():
    # RF-8 vale "cualquiera sea el valor de `correccion`": esta función ni lo recibe.
    # La verificación integrada con "desactivar" se hace en T9.
    import inspect

    assert "correccion" not in inspect.signature(evaluar_confirmacion).parameters


def test_rf8_no_modifica_la_tabla_de_entrada():
    tabla = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5])
    copia = tabla.copy()

    evaluar_confirmacion(tabla, "")

    pd.testing.assert_frame_equal(tabla, copia)


# --- T8: decisión en modo "auto" --------------------------------------------------------


def _factor(fc=1.2, p_valor=0.001, n_bajo=3, n_fuera=3, media_bajo=0.5):
    return FactorMalla(fc=fc, p_valor=p_valor, n_bajo=n_bajo, n_fuera=n_fuera, media_bajo=media_bajo)


def test_rf6_el_factor_incluye_la_media_bajo_malla():
    factor = calcular_factor(_tabla(fuera=[0.58, 0.60, 0.62], bajo=[0.48, 0.50, 0.52]))

    assert factor.media_bajo == pytest.approx(0.5)
    assert calcular_factor(_tabla(fuera=[0.6], bajo=[])).media_bajo is None


def test_rf7_corrige_con_p_menor_que_alfa_grupos_validos_y_media_positiva():
    decision = decidir_modo_auto(_factor(p_valor=0.01))

    assert decision == DecisionCorreccion(corregir=True, advertencia=None)


def test_rf11_p_igual_a_alfa_no_corrige_porque_la_condicion_es_estrictamente_menor():
    decision = decidir_modo_auto(_factor(p_valor=0.05))

    assert decision.corregir is False
    assert decision.advertencia.codigo == "NO_SIGNIFICATIVO"


def test_rf11_p_mayor_o_igual_a_alfa_no_corrige_y_la_advertencia_incluye_el_p_valor():
    decision = decidir_modo_auto(_factor(p_valor=0.1234))

    assert decision.corregir is False
    assert decision.advertencia.codigo == "NO_SIGNIFICATIVO"
    assert "0.1234" in decision.advertencia.mensaje


@pytest.mark.parametrize("n_bajo,n_fuera", [(1, 5), (5, 1), (1, 1)])
def test_rf11_un_grupo_con_menos_de_2_plantas_no_corrige(n_bajo, n_fuera):
    decision = decidir_modo_auto(_factor(n_bajo=n_bajo, n_fuera=n_fuera, p_valor=None))

    assert decision.corregir is False
    assert decision.advertencia.codigo == "GRUPO_CHICO"


@pytest.mark.parametrize("media", [0.0, -0.2])
def test_rf11_media_bajo_malla_no_positiva_no_corrige(media):
    decision = decidir_modo_auto(_factor(media_bajo=media))

    assert decision.corregir is False
    assert decision.advertencia.codigo == "MEDIA_NO_POSITIVA"


@pytest.mark.parametrize("n_bajo,n_fuera", [(0, 6), (6, 0)])
def test_rf10_sin_plantas_bajo_malla_o_todas_bajo_malla_no_corrige_y_no_da_error(n_bajo, n_fuera):
    decision = decidir_modo_auto(_factor(fc=None, p_valor=None, n_bajo=n_bajo, n_fuera=n_fuera, media_bajo=None))

    assert decision == DecisionCorreccion(corregir=False, advertencia=None)


def test_rf11_si_los_grupos_son_validos_pero_no_hay_p_valor_no_corrige_con_advertencia():
    # Caso no previsto en la spec: ambos grupos sin variación (decisión provisional).
    decision = decidir_modo_auto(_factor(p_valor=None))

    assert decision.corregir is False
    assert decision.advertencia.codigo == "P_NO_DISPONIBLE"


def test_rf7_alfa_y_minimo_de_plantas_son_parametros():
    assert decidir_modo_auto(_factor(p_valor=0.04), alfa=0.01).corregir is False
    assert decidir_modo_auto(_factor(p_valor=0.04), alfa=0.10).corregir is True
    assert decidir_modo_auto(_factor(n_bajo=3), min_plantas_grupo=4).advertencia.codigo == "GRUPO_CHICO"


def test_rf7_integrado_con_calcular_factor_grupos_muy_distintos_corrigen():
    factor = calcular_factor(_tabla(fuera=[0.59, 0.60, 0.61, 0.60], bajo=[0.44, 0.45, 0.46, 0.45]))

    assert decidir_modo_auto(factor).corregir is True


def test_rf11_integrado_con_calcular_factor_grupos_parecidos_no_corrigen():
    factor = calcular_factor(_tabla(fuera=[0.50, 0.52, 0.48, 0.51], bajo=[0.51, 0.49, 0.50, 0.52]))

    decision = decidir_modo_auto(factor)

    assert decision.corregir is False
    assert decision.advertencia.codigo == "NO_SIGNIFICATIVO"
