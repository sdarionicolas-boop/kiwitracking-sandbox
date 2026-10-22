"""Reproducción de los resultados publicados (notebook 03, v1.1, lote "El Abrojito", 159 plantas).

Los datos de `tests/golden/` son la verdad contra la que se compara el núcleo (constitución #5).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.huella import huella

GOLDEN = Path(__file__).parent / "golden" / "datos_plantas_completos.csv"


@pytest.fixture(scope="module")
def golden():
    return pd.read_csv(GOLDEN, encoding="utf-8").set_index("id")


@pytest.fixture(scope="module")
def entrada(golden):
    return golden.reset_index()[["id", "KVPI_mean", "KVPI_std", "bajo_malla"]]


def _analizar(entrada, estado_frio, **kwargs):
    return analizar(
        entrada, huella_confirmada=huella(entrada), estado_frio_ultima_campana=estado_frio, **kwargs
    )


@pytest.fixture(scope="module")
def con_frio_deficiente(entrada):
    return _analizar(entrada, "Deficiente")


@pytest.fixture(scope="module")
def sin_ajuste_de_frio(entrada):
    return _analizar(entrada, "Adecuado")


def test_criterio2_kvpi_corregido_y_estabilidad_coinciden_con_el_golden(con_frio_deficiente, golden):
    resultado = con_frio_deficiente.tabla.set_index("id").loc[golden.index]

    pd.testing.assert_series_equal(resultado["KVPI_corregido"], golden["KVPI_corregido"], atol=1e-6, rtol=0)
    pd.testing.assert_series_equal(resultado["estabilidad"], golden["estabilidad"], atol=1e-6, rtol=0)


def test_criterio2_ambiente_y_recomendacion_coinciden_exactamente(con_frio_deficiente, golden):
    resultado = con_frio_deficiente.tabla.set_index("id").loc[golden.index]

    assert resultado["ambiente"].tolist() == golden["ambiente"].tolist()
    assert resultado["recomendacion"].tolist() == golden["recomendacion"].tolist()


def test_criterio2_los_umbrales_coinciden_con_los_del_golden_y_con_los_publicados(con_frio_deficiente, golden):
    resumen = con_frio_deficiente.resumen

    assert resumen.p33 == pytest.approx(np.percentile(golden["KVPI_corregido"], 33), abs=1e-6)
    assert resumen.p66 == pytest.approx(np.percentile(golden["KVPI_corregido"], 66), abs=1e-6)
    assert resumen.p75_estabilidad == pytest.approx(np.percentile(golden["estabilidad"], 75), abs=1e-6)
    # Valores publicados en metadata_ejecucion.txt (3 decimales): "Bajo <= 0.536 | Alto >= 0.564"
    assert resumen.p33 == pytest.approx(0.536, abs=5e-4)
    assert resumen.p66 == pytest.approx(0.564, abs=5e-4)


def test_criterio3_el_fc_calculado_es_1_2262(con_frio_deficiente):
    assert con_frio_deficiente.resumen.fc == pytest.approx(1.2262, abs=1e-3)


def test_criterio3_la_diferencia_entre_grupos_es_altamente_significativa(con_frio_deficiente):
    # La documentación dice p < 0.001
    assert con_frio_deficiente.resumen.p_valor < 0.001


def test_criterio4_el_cruce_de_grupos_da_53_plantas_bajo_malla_y_106_fuera(con_frio_deficiente):
    assert con_frio_deficiente.resumen.n_bajo_malla == 53
    assert con_frio_deficiente.resumen.n_fuera_malla == 106


def test_criterio2_la_distribucion_de_ambientes_es_54_53_52(con_frio_deficiente):
    ambientes = con_frio_deficiente.tabla["ambiente"].value_counts().to_dict()

    assert ambientes == {"Alto Potencial": 54, "Limitante": 53, "Transicional": 52}


def test_criterio2_con_frio_deficiente_no_hay_mantener_y_hay_19_intervenir(con_frio_deficiente):
    recomendaciones = con_frio_deficiente.tabla["recomendacion"].value_counts().to_dict()

    assert recomendaciones.get("Mantener", 0) == 0
    assert recomendaciones["Intervenir"] == 19


def test_criterio5_sin_ajuste_de_frio_el_lote_da_15_mantener_y_19_intervenir(sin_ajuste_de_frio):
    recomendaciones = sin_ajuste_de_frio.tabla["recomendacion"].value_counts().to_dict()

    assert recomendaciones["Mantener"] == 15
    assert recomendaciones["Intervenir"] == 19


def test_el_analisis_del_lote_de_referencia_no_genera_advertencias(con_frio_deficiente):
    assert con_frio_deficiente.advertencias == []


def test_control_negativo_sin_corregir_los_resultados_ya_no_coinciden_con_el_golden(entrada, golden):
    # Garantiza que este archivo puede fallar: sin corrección, las plantas bajo malla se alejan del golden.
    sin_corregir = _analizar(entrada, "Deficiente", correccion="desactivar").tabla.set_index("id").loc[golden.index]

    diferencia = (sin_corregir["KVPI_corregido"] - golden["KVPI_corregido"]).abs().max()
    assert diferencia > 0.05
    assert sin_corregir["ambiente"].tolist() != golden["ambiente"].tolist()
