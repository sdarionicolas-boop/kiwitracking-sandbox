"""Campaña, completitud del GDD e integración con `analizar()` sobre el clima y el lote reales (spec 002, criterios 5 a 7).

Las horas de 2024 y 2025 dependen de días interpolados, no medidos por INTA: ver `AGENTS.md`.
"""

from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.campana import estado_frio_de_campana
from kiwitracking.clima import calcular_clima
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.huella import huella

GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture(scope="module")
def clima():
    return calcular_clima(pd.read_csv(GOLDEN / "clima_diario.csv", encoding="utf-8")[["date", "Tmax", "Tmin"]], ParametrosClima())


@pytest.fixture(scope="module")
def lote():
    return pd.read_csv(GOLDEN / "datos_plantas_completos.csv", encoding="utf-8")[["id", "KVPI_mean", "KVPI_std", "bajo_malla"]]


def _codigos(estado):
    return [a.codigo for a in estado.advertencias]


# --- Criterio 5: elección de la campaña ---------------------------------------------------------


def test_criterio5_sin_campana_es_el_invierno_2025_adecuado_con_su_cobertura_y_su_aviso(clima):
    estado = estado_frio_de_campana(clima)

    assert (estado.periodo, estado.estado) == (2025, "Adecuado")
    assert estado.cobertura == pytest.approx(119 / 123, abs=1e-4) and estado.cobertura == pytest.approx(0.9675, abs=1e-4)
    assert estado.hueco_maximo == 4
    assert "CAMPANA_NO_INDICADA" in _codigos(estado)


def test_criterio5_con_campana_2024_es_el_invierno_2024_optimo_sin_el_aviso_de_campana_no_indicada(clima):
    estado = estado_frio_de_campana(clima, campana=2024)

    assert (estado.periodo, estado.estado) == (2024, "Óptimo")
    assert estado.horas == pytest.approx(1128.8, abs=0.05)
    assert "CAMPANA_NO_INDICADA" not in _codigos(estado)


# --- Criterio 6: completitud del GDD por temporada ----------------------------------------------


def test_criterio6_las_temporadas_de_gdd_2019_2020_2021_2023_y_2024_son_completas(clima):
    gdd = clima.gdd.set_index("temporada")

    assert gdd.loc[[2019, 2020, 2021, 2023, 2024], "completo"].all()


def test_criterio6_la_temporada_2022_es_incompleta_por_un_hueco_de_34_dias_aunque_su_cobertura_sea_0_901(clima):
    fila = clima.gdd.set_index("temporada").loc[2022]

    assert fila["cobertura"] == pytest.approx(0.901, abs=0.001) and fila["cobertura"] >= 0.9
    assert fila["hueco_maximo"] == 34
    assert not fila["completo"]


def test_criterio6_las_temporadas_de_los_bordes_2018_y_2025_son_incompletas(clima):
    gdd = clima.gdd.set_index("temporada")

    assert not gdd.loc[2018, "completo"] and not gdd.loc[2025, "completo"]


def test_criterio6_las_temporadas_incompletas_dan_aviso_de_periodo_incompleto(clima):
    avisos = [a.mensaje for a in clima.advertencias if a.codigo == "PERIODO_INCOMPLETO" and a.mensaje.startswith("GDD")]

    assert [any(f"temporada {t}" in m for m in avisos) for t in (2018, 2022, 2025)] == [True, True, True]


# --- Criterio 7: integración con analizar() -----------------------------------------------------


@pytest.mark.parametrize("campana", [None, 2024])
def test_criterio7_cualquiera_de_los_dos_estados_da_16_mantener_y_19_intervenir_sobre_el_lote_real(clima, lote, campana):
    estado = estado_frio_de_campana(clima, campana=campana)

    resultado = analizar(lote, huella_confirmada=huella(lote), estado_frio_ultima_campana=estado.estado)

    recomendaciones = resultado.tabla["recomendacion"].value_counts().to_dict()
    assert (recomendaciones["Mantener"], recomendaciones["Intervenir"]) == (16, 19)


# --- C3: una temporada de GDD completa con cobertura menor que 1 no avisa (decisión del 22/10/2026) ---


def test_c3_la_temporada_2024_de_gdd_es_completa_con_cobertura_0_989_y_no_genera_ningun_aviso(clima):
    fila = clima.gdd.set_index("temporada").loc[2024]

    assert fila["completo"] and fila["cobertura"] == pytest.approx(361 / 365)
    assert not [a for a in clima.advertencias if a.mensaje.startswith("GDD, temporada 2024")]
