import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.clasificacion import calcular_umbrales
from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada, Resultado


def _tabla_12():
    """8 plantas fuera de malla (KVPI ~0.61) y 4 bajo malla (KVPI ~0.46): FC ~1.35, p muy chico."""
    fuera = [0.62, 0.60, 0.64, 0.58, 0.66, 0.61, 0.59, 0.63]
    std_fuera = [0.02, 0.05, 0.02, 0.05, 0.03, 0.04, 0.05, 0.02]
    bajo = [0.46, 0.44, 0.48, 0.45]
    std_bajo = [0.03, 0.04, 0.02, 0.05]
    return pd.DataFrame(
        {
            "id": range(1, 13),
            "KVPI_mean": fuera + bajo,
            "KVPI_std": std_fuera + std_bajo,
            "bajo_malla": [0] * 8 + [1] * 4,
        }
    )


def _analizar_ok(tabla=None, **kwargs):
    tabla = _tabla_12() if tabla is None else tabla
    kwargs.setdefault("huella_confirmada", huella(tabla))
    kwargs.setdefault("estado_frio_ultima_campana", "Adecuado")
    return analizar(tabla, **kwargs)


def test_rf26_el_flujo_completo_devuelve_tabla_resumen_y_advertencias():
    tabla = _tabla_12()

    resultado = _analizar_ok(tabla)

    assert isinstance(resultado, Resultado)
    assert list(resultado.tabla.columns) == list(tabla.columns) + [
        "KVPI_corregido", "estabilidad", "ambiente", "recomendacion",
    ]
    assert resultado.tabla["id"].tolist() == tabla["id"].tolist()
    assert resultado.advertencias == []


def test_rf26_el_resumen_trae_fc_p_tamanos_umbrales_huella_y_si_se_corrigio():
    tabla = _tabla_12()

    resumen = _analizar_ok(tabla).resumen

    assert resumen.correccion_aplicada is True
    assert resumen.fc == pytest.approx(1.3470, abs=1e-3)
    assert resumen.p_valor < 0.001
    assert (resumen.n_bajo_malla, resumen.n_fuera_malla) == (4, 8)
    assert resumen.huella == huella(tabla)


def test_rf26_los_umbrales_del_resumen_son_los_de_la_tabla_resultante():
    resultado = _analizar_ok()

    umbrales = calcular_umbrales(resultado.tabla)

    assert resultado.resumen.p33 == pytest.approx(umbrales.p33)
    assert resultado.resumen.p66 == pytest.approx(umbrales.p66)
    assert resultado.resumen.p75_estabilidad == pytest.approx(umbrales.p75_estabilidad)


def test_rf7_con_correccion_las_plantas_bajo_malla_suben_y_las_demas_no():
    tabla = _tabla_12()

    resultado = _analizar_ok(tabla)

    bajo = tabla["bajo_malla"] == 1
    assert (resultado.tabla.loc[bajo, "KVPI_corregido"] > tabla.loc[bajo, "KVPI_mean"]).all()
    assert resultado.tabla.loc[~bajo, "KVPI_corregido"].tolist() == tabla.loc[~bajo, "KVPI_mean"].tolist()


def test_rf8_sin_huella_no_se_corrige_y_se_avisa():
    resultado = analizar(_tabla_12(), estado_frio_ultima_campana="Adecuado")

    assert resultado.resumen.correccion_aplicada is False
    assert [a.codigo for a in resultado.advertencias] == ["FALTA_CONFIRMACION"]
    assert resultado.tabla["KVPI_corregido"].tolist() == resultado.tabla["KVPI_mean"].tolist()


def test_rf25_con_frio_deficiente_no_queda_ninguna_planta_en_mantener():
    con_frio_ok = _analizar_ok(estado_frio_ultima_campana="Adecuado").tabla
    deficiente = _analizar_ok(estado_frio_ultima_campana="Deficiente").tabla

    assert (con_frio_ok["recomendacion"] == "Mantener").any()
    assert not (deficiente["recomendacion"] == "Mantener").any()


def test_rf25_sin_estado_de_frio_se_avisa_sin_estado_frio():
    resultado = _analizar_ok(estado_frio_ultima_campana=None)

    assert [a.codigo for a in resultado.advertencias] == ["SIN_ESTADO_FRIO"]


def test_rf2_las_plantas_con_kvpi_vacio_se_excluyen_y_se_avisa():
    tabla = _tabla_12()
    tabla.loc[[0, 9], "KVPI_mean"] = float("nan")  # una fuera de malla y una bajo malla

    resultado = _analizar_ok(tabla, huella_confirmada=huella(tabla))

    assert len(resultado.tabla) == 10
    assert 1 not in resultado.tabla["id"].tolist() and 10 not in resultado.tabla["id"].tolist()
    assert resultado.advertencias[0].codigo == "PLANTAS_EXCLUIDAS"


def test_rf9_la_huella_se_calcula_sobre_la_tabla_de_entrada_completa_aunque_se_excluyan_plantas():
    tabla = _tabla_12()
    tabla.loc[9, "KVPI_mean"] = float("nan")  # una planta bajo malla se excluye por no tener KVPI
    huella_del_mapa = huella(tabla)  # lo que el usuario vio y confirmó

    resultado = analizar(tabla, huella_confirmada=huella_del_mapa, estado_frio_ultima_campana="Adecuado")

    assert resultado.resumen.correccion_aplicada is True
    assert resultado.resumen.huella == huella_del_mapa
    assert "HUELLA_NO_COINCIDE" not in [a.codigo for a in resultado.advertencias]


def test_rf21_una_planta_con_std_cero_avisa_y_queda_en_observar():
    tabla = _tabla_12()
    tabla.loc[2, "KVPI_std"] = 0.0  # la planta 3 era "Mantener"

    resultado = _analizar_ok(tabla)

    assert "STD_CERO" in [a.codigo for a in resultado.advertencias]
    fila = resultado.tabla.loc[resultado.tabla["id"] == 3].iloc[0]
    assert pd.isna(fila["estabilidad"])
    assert fila["recomendacion"] == "Observar"


def test_rf26_el_orden_de_las_advertencias_sigue_el_del_flujo():
    tabla = _tabla_12()
    tabla.loc[0, "KVPI_mean"] = float("nan")
    tabla.loc[2, "KVPI_std"] = 0.0

    resultado = analizar(tabla)  # sin huella y sin estado de frío

    assert [a.codigo for a in resultado.advertencias] == [
        "PLANTAS_EXCLUIDAS", "FALTA_CONFIRMACION", "STD_CERO", "SIN_ESTADO_FRIO",
    ]


def test_rf11_si_no_queda_ninguna_planta_con_kvpi_da_error():
    tabla = _tabla_12()
    tabla["KVPI_mean"] = float("nan")

    with pytest.raises(ErrorDeEntrada, match="(?i)ninguna planta"):
        analizar(tabla)


@pytest.mark.parametrize(
    "kwargs",
    [{"correccion": "siempre"}, {"estado_frio_ultima_campana": "deficiente"}],
)
def test_rf14_los_parametros_invalidos_dan_error(kwargs):
    with pytest.raises(ErrorDeEntrada):
        analizar(_tabla_12(), **kwargs)


def test_rf1_una_tabla_sin_columnas_obligatorias_da_error():
    with pytest.raises(ErrorDeEntrada, match="KVPI_std"):
        analizar(_tabla_12().drop(columns=["KVPI_std"]))


def test_rf12_los_modos_forzar_y_desactivar_llegan_hasta_el_resultado():
    tabla = _tabla_12()
    comunes = {"huella_confirmada": huella(tabla), "estado_frio_ultima_campana": "Adecuado"}

    forzar = analizar(tabla, correccion="forzar", **comunes)
    desactivar = analizar(tabla, correccion="desactivar", **comunes)

    assert forzar.resumen.correccion_aplicada is True
    assert [a.codigo for a in forzar.advertencias] == ["CORRECCION_FORZADA"]
    assert desactivar.resumen.correccion_aplicada is False
    assert desactivar.advertencias == []


def test_rf26_no_modifica_la_tabla_de_entrada():
    tabla = _tabla_12()
    tabla.loc[0, "KVPI_mean"] = float("nan")
    copia = tabla.copy()

    analizar(tabla, huella_confirmada=huella(tabla))

    pd.testing.assert_frame_equal(tabla, copia)
