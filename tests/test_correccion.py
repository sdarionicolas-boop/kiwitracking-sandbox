import pandas as pd
import pytest
from scipy import stats

from kiwitracking.correccion import (
    DecisionCorreccion,
    FactorMalla,
    aplicar_correccion,
    calcular_factor,
    decidir_correccion,
    decidir_modo_auto,
    evaluar_confirmacion,
    resolver_correccion,
)
from kiwitracking.resultado import ErrorDeEntrada
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


def test_rf6_por_defecto_usa_la_prueba_de_welch_que_no_supone_varianzas_iguales():
    fuera = [1.0, 2.0, 3.0]
    bajo = [2.0, 4.0, 6.0, 8.0, 10.0]
    welch = stats.ttest_ind(fuera, bajo, equal_var=False).pvalue
    student = stats.ttest_ind(fuera, bajo, equal_var=True).pvalue
    assert welch != pytest.approx(student, abs=1e-3)  # el ejemplo distingue ambas pruebas

    factor = calcular_factor(_tabla(fuera=fuera, bajo=bajo))

    assert factor.p_valor == pytest.approx(welch)


def test_rf6_con_prueba_t_student_usa_la_de_varianzas_iguales_como_en_v1_1():
    fuera = [1.0, 2.0, 3.0]
    bajo = [2.0, 4.0, 6.0, 8.0, 10.0]

    factor = calcular_factor(_tabla(fuera=fuera, bajo=bajo), prueba_t="student")

    assert factor.p_valor == pytest.approx(stats.ttest_ind(fuera, bajo, equal_var=True).pvalue)


def test_rf6_welch_explicito_es_lo_mismo_que_el_valor_por_defecto():
    tabla = _tabla(fuera=[0.59, 0.60, 0.61, 0.60], bajo=[0.44, 0.45, 0.46, 0.45])

    assert calcular_factor(tabla, prueba_t="welch") == calcular_factor(tabla)


def test_rf6_el_fc_y_los_tamanos_de_grupo_no_dependen_de_la_prueba():
    tabla = _tabla(fuera=[0.59, 0.60, 0.61, 0.60], bajo=[0.44, 0.45, 0.46])

    welch = calcular_factor(tabla, prueba_t="welch")
    student = calcular_factor(tabla, prueba_t="student")

    assert (welch.fc, welch.n_bajo, welch.n_fuera, welch.media_bajo) == (
        student.fc, student.n_bajo, student.n_fuera, student.media_bajo,
    )


def test_rf6_con_varianzas_iguales_y_grupos_del_mismo_tamano_ambas_pruebas_coinciden():
    tabla = _tabla(fuera=[1.0, 2.0, 3.0], bajo=[2.0, 3.0, 4.0])

    assert calcular_factor(tabla, prueba_t="welch").p_valor == pytest.approx(
        calcular_factor(tabla, prueba_t="student").p_valor
    )


def test_rf6_welch_calcula_el_p_valor_aunque_un_grupo_no_tenga_variacion():
    # Un grupo con todos los valores iguales y el otro no: la prueba de Welch sigue siendo calculable.
    factor = calcular_factor(_tabla(fuera=[0.60, 0.60, 0.60], bajo=[0.40, 0.50, 0.45]))

    assert factor.p_valor is not None and 0 <= factor.p_valor <= 1


@pytest.mark.parametrize("valor", ["Welch", "t", "", None])
def test_rf28_calcular_factor_con_una_prueba_invalida_da_error_que_nombra_los_valores_permitidos(valor):
    with pytest.raises(ErrorDeEntrada) as error:
        calcular_factor(_tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5]), prueba_t=valor)

    assert "welch" in str(error.value) and "student" in str(error.value)


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


# --- T9: modos "forzar" y "desactivar", y aplicación de la corrección --------------------


def test_rf13_desactivar_nunca_corrige_aunque_p_sea_chico():
    decision = decidir_correccion(_factor(p_valor=0.0001), "desactivar")

    assert decision == DecisionCorreccion(corregir=False, advertencia=None)


def test_rf12_forzar_corrige_con_p_alto_y_avisa_con_el_p_valor():
    decision = decidir_correccion(_factor(p_valor=0.3), "forzar")

    assert decision.corregir is True
    assert decision.advertencia.codigo == "CORRECCION_FORZADA"
    assert "0.3" in decision.advertencia.mensaje


def test_rf12_forzar_tambien_avisa_si_el_p_valor_ya_era_significativo():
    decision = decidir_correccion(_factor(p_valor=0.001), "forzar")

    assert decision.corregir is True
    assert decision.advertencia.codigo == "CORRECCION_FORZADA"


def test_rf12_forzar_corrige_aunque_no_haya_p_valor_y_lo_dice():
    decision = decidir_correccion(_factor(p_valor=None), "forzar")

    assert decision.corregir is True
    assert decision.advertencia.codigo == "CORRECCION_FORZADA"
    assert "no disponible" in decision.advertencia.mensaje


@pytest.mark.parametrize("n_bajo,n_fuera", [(1, 5), (5, 1), (0, 5), (5, 0)])
def test_rf12_forzar_con_un_grupo_de_menos_de_2_plantas_no_corrige_y_da_la_causa(n_bajo, n_fuera):
    decision = decidir_correccion(_factor(n_bajo=n_bajo, n_fuera=n_fuera), "forzar")

    assert decision.corregir is False
    assert decision.advertencia.codigo == "GRUPO_CHICO"


@pytest.mark.parametrize("media", [0.0, -0.3])
def test_rf12_forzar_con_media_bajo_malla_no_positiva_no_corrige_y_da_la_causa(media):
    decision = decidir_correccion(_factor(media_bajo=media), "forzar")

    assert decision.corregir is False
    assert decision.advertencia.codigo == "MEDIA_NO_POSITIVA"


def test_rf7_decidir_correccion_en_auto_delega_en_decidir_modo_auto():
    for factor in (_factor(p_valor=0.01), _factor(p_valor=0.4), _factor(n_bajo=1, p_valor=None)):
        assert decidir_correccion(factor, "auto") == decidir_modo_auto(factor)


def test_rf14_decidir_correccion_con_modo_invalido_da_error():
    with pytest.raises(ErrorDeEntrada, match="auto"):
        decidir_correccion(_factor(), "siempre")


def test_rf7_aplicar_correccion_multiplica_solo_las_plantas_bajo_malla():
    tabla = _tabla(fuera=[0.60, 0.62], bajo=[0.50, 0.40])

    resultado = aplicar_correccion(tabla, fc=1.2)

    assert resultado["KVPI_corregido"].tolist() == pytest.approx([0.60, 0.62, 0.60, 0.48])


def test_rf7_aplicar_correccion_conserva_las_columnas_y_no_modifica_la_entrada():
    tabla = _tabla(fuera=[0.60], bajo=[0.50])
    copia = tabla.copy()

    resultado = aplicar_correccion(tabla, fc=1.2)

    assert list(resultado.columns) == list(copia.columns) + ["KVPI_corregido"]
    pd.testing.assert_frame_equal(tabla, copia)


def test_rf11_aplicar_correccion_sin_fc_deja_el_kvpi_corregido_igual_al_original():
    tabla = _tabla(fuera=[0.60], bajo=[0.50])

    resultado = aplicar_correccion(tabla, fc=None)

    assert resultado["KVPI_corregido"].tolist() == tabla["KVPI_mean"].tolist()


def _tabla_distinta():
    return _tabla(fuera=[0.59, 0.60, 0.61, 0.60], bajo=[0.44, 0.45, 0.46, 0.45])


def test_rf7_resolver_en_auto_con_huella_correcta_corrige_y_no_avisa():
    tabla = _tabla_distinta()

    r = resolver_correccion(tabla, "auto", huella(tabla))

    assert r.aplicada is True
    assert r.advertencias == []
    assert r.factor.fc == pytest.approx(0.60 / 0.45)
    bajo = r.tabla["bajo_malla"] == 1
    esperado = (tabla.loc[bajo, "KVPI_mean"] * r.factor.fc).tolist()
    assert r.tabla.loc[bajo, "KVPI_corregido"].tolist() == pytest.approx(esperado)
    assert r.tabla.loc[~bajo, "KVPI_corregido"].tolist() == tabla.loc[~bajo, "KVPI_mean"].tolist()


@pytest.mark.parametrize("modo", ["auto", "forzar"])
def test_rf8_sin_huella_no_se_corrige_y_se_avisa_pero_el_factor_se_calcula(modo):
    tabla = _tabla_distinta()

    r = resolver_correccion(tabla, modo, "")

    assert r.aplicada is False
    assert [a.codigo for a in r.advertencias] == ["FALTA_CONFIRMACION"]
    assert r.tabla["KVPI_corregido"].tolist() == tabla["KVPI_mean"].tolist()
    assert r.factor.fc is not None


def test_rf8_con_desactivar_y_huella_vacia_se_sigue_avisando_la_falta_de_confirmacion():
    # La prueba integrada que quedó pendiente de T7 (decisión provisional: se avisa igual).
    r = resolver_correccion(_tabla_distinta(), "desactivar", "")

    assert r.aplicada is False
    assert [a.codigo for a in r.advertencias] == ["FALTA_CONFIRMACION"]


def test_rf9_huella_que_no_coincide_bloquea_incluso_el_modo_forzar():
    r = resolver_correccion(_tabla_distinta(), "forzar", "000000000000")

    assert r.aplicada is False
    assert [a.codigo for a in r.advertencias] == ["HUELLA_NO_COINCIDE"]


def test_rf13_desactivar_con_huella_correcta_no_corrige_y_no_avisa():
    tabla = _tabla_distinta()

    r = resolver_correccion(tabla, "desactivar", huella(tabla))

    assert r.aplicada is False
    assert r.advertencias == []
    assert r.tabla["KVPI_corregido"].tolist() == tabla["KVPI_mean"].tolist()


def test_rf12_resolver_forzar_con_grupos_parecidos_corrige_y_avisa_correccion_forzada():
    tabla = _tabla(fuera=[0.50, 0.52, 0.48, 0.51], bajo=[0.51, 0.49, 0.50, 0.52])

    r = resolver_correccion(tabla, "forzar", huella(tabla))

    assert r.aplicada is True
    assert [a.codigo for a in r.advertencias] == ["CORRECCION_FORZADA"]


def test_rf10_resolver_sin_plantas_bajo_malla_no_corrige_y_no_avisa():
    tabla = _tabla(fuera=[0.5, 0.6, 0.7], bajo=[])

    r = resolver_correccion(tabla, "auto", huella(tabla))

    assert r.aplicada is False
    assert r.advertencias == []
    assert r.tabla["KVPI_corregido"].tolist() == tabla["KVPI_mean"].tolist()


def test_rf14_resolver_con_modo_invalido_da_error():
    tabla = _tabla_distinta()

    with pytest.raises(ErrorDeEntrada):
        resolver_correccion(tabla, "siempre", huella(tabla))


def test_rf7_resolver_no_modifica_la_tabla_de_entrada():
    tabla = _tabla_distinta()
    copia = tabla.copy()

    resolver_correccion(tabla, "auto", huella(tabla))

    pd.testing.assert_frame_equal(tabla, copia)


# --- T15: huella de referencia (la confirmación se compara con la tabla completa de entrada) ---


def test_rf9_evaluar_confirmacion_compara_contra_la_huella_de_referencia_si_se_da():
    completa = _tabla(fuera=[0.6, 0.6], bajo=[0.5, 0.5, 0.5])
    filtrada = completa.iloc[:-1]  # se perdió una planta bajo malla: otra huella
    assert huella(completa) != huella(filtrada)

    assert evaluar_confirmacion(filtrada, huella(completa), huella_referencia=huella(completa)) is None
    assert evaluar_confirmacion(filtrada, huella(completa)).codigo == "HUELLA_NO_COINCIDE"


def test_rf9_resolver_acepta_la_huella_de_referencia():
    completa = _tabla_distinta()
    filtrada = completa.iloc[:-1]

    r = resolver_correccion(filtrada, "auto", huella(completa), huella_referencia=huella(completa))

    assert r.aplicada is True


# --- T31 (Cambio 3): prueba_t en resolver_correccion --------------------------------------


def test_rf6_resolver_correccion_propaga_la_prueba_t_al_factor():
    tabla = _tabla(fuera=[1.0, 2.0, 3.0, 2.5], bajo=[2.0, 4.0, 6.0, 8.0, 10.0])

    welch = resolver_correccion(tabla, "forzar", huella(tabla), prueba_t="welch").factor.p_valor
    student = resolver_correccion(tabla, "forzar", huella(tabla), prueba_t="student").factor.p_valor

    assert welch == calcular_factor(tabla, prueba_t="welch").p_valor
    assert student == calcular_factor(tabla, prueba_t="student").p_valor
    assert welch != pytest.approx(student)


def test_rf28_resolver_correccion_con_prueba_invalida_da_error():
    tabla = _tabla_distinta()

    with pytest.raises(ErrorDeEntrada, match="welch"):
        resolver_correccion(tabla, "auto", huella(tabla), prueba_t="z")


def test_rf28_validar_parametros_acepta_las_dos_pruebas():
    from kiwitracking.validacion import validar_parametros

    validar_parametros(prueba_t="welch")
    validar_parametros(prueba_t="student")
