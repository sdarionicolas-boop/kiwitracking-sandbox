"""Procedencia del clima de referencia (T2.0) y cuánto dependen de ella los resultados de los dos últimos inviernos.

No prueban el software: dejan escrito, y vigilado por tests, qué parte del archivo `tests/golden/clima_diario.csv`
está verificada contra el Excel de INTA y qué resultados dependen de la parte que no lo está.
"""

from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.campana import estado_frio_de_campana
from kiwitracking.clima import calcular_clima
from kiwitracking.clima_parametros import ParametrosClima

ARCHIVO = Path(__file__).parent / "golden" / "clima_diario.csv"


@pytest.fixture(scope="module")
def clima():
    return pd.read_csv(ARCHIVO, encoding="utf-8")


def _estado(tabla):
    clima_calculado = calcular_clima(tabla[["date", "Tmax", "Tmin"]], ParametrosClima())
    return clima_calculado, estado_frio_de_campana(clima_calculado)


# --- el archivo ---------------------------------------------------------------------------


def test_t20_el_archivo_trae_las_columnas_acordadas_y_2604_dias_de_2019_a_2026(clima):
    assert list(clima.columns) == ["date", "Tmax", "Tmin", "origen"]
    assert len(clima) == 2604
    assert (clima["date"].min(), clima["date"].max()) == ("2019-01-01", "2026-03-28")


def test_t20_no_hay_temperaturas_vacias_pero_faltan_40_fechas_que_no_se_rellenan(clima):
    assert clima[["Tmax", "Tmin"]].notna().all().all()
    fechas = pd.to_datetime(clima["date"])
    esperadas = pd.date_range(fechas.min(), fechas.max())

    assert len(esperadas.difference(fechas)) == 40
    assert fechas.is_unique


def test_t20_2303_dias_estan_verificados_contra_inta_y_301_no(clima):
    assert clima["origen"].value_counts().to_dict() == {"INTA_verificado": 2303, "no_verificado": 301}


def test_t20_los_dias_no_verificados_son_los_del_hueco_del_excel_y_los_posteriores_a_su_fin(clima):
    no_verificados = pd.to_datetime(clima.loc[clima["origen"] == "no_verificado", "date"])

    assert no_verificados.min() == pd.Timestamp("2019-09-24")
    assert (no_verificados > "2025-07-28").sum() == 243   # después del fin del Excel de INTA
    assert (no_verificados <= "2025-07-28").sum() == 58   # días vacíos en ese Excel


def test_t20_35_dias_no_verificados_tienen_valores_derivados_con_mas_de_un_decimal(clima):
    no_verificados = clima[clima["origen"] == "no_verificado"]
    decimales = no_verificados["Tmax"].map(lambda v: len(repr(v).split(".")[-1]))

    assert (decimales > 1).sum() == 35
    assert (clima.loc[clima["origen"] == "INTA_verificado", "Tmax"].map(lambda v: len(repr(v).split(".")[-1])) == 1).all()


# --- cuánto dependen los resultados de los días no verificados -------------------------------


def test_t20_con_el_archivo_completo_el_invierno_2024_es_optimo_y_el_2025_adecuado(clima):
    calculado, ultimo = _estado(clima)

    frio = calculado.frio.set_index("periodo")
    assert frio.loc[2024, "Horas_Frio"] == pytest.approx(1128.8, abs=0.05) and frio.loc[2024, "estado_frio"] == "Óptimo"
    assert frio.loc[2025, "Horas_Frio"] == pytest.approx(834.2, abs=0.05) and frio.loc[2025, "estado_frio"] == "Adecuado"
    assert (ultimo.periodo, ultimo.estado) == (2025, "Adecuado")


def test_t20_sin_los_dias_no_verificados_los_inviernos_2024_y_2025_no_son_clasificables(clima):
    solo_inta = clima[clima["origen"] == "INTA_verificado"]

    calculado, ultimo = _estado(solo_inta)

    frio = calculado.frio.set_index("periodo")
    assert pd.isna(frio.loc[2024, "estado_frio"]) and frio.loc[2024, "cobertura"] == pytest.approx(0.789, abs=0.001)
    assert pd.isna(frio.loc[2025, "estado_frio"]) and frio.loc[2025, "cobertura"] == pytest.approx(0.626, abs=0.001)
    assert (ultimo.periodo, ultimo.estado) == (2023, "Adecuado")


def test_t20_los_inviernos_2019_a_2022_no_dependen_de_los_dias_no_verificados(clima):
    completo = calcular_clima(clima[["date", "Tmax", "Tmin"]], ParametrosClima()).frio.set_index("periodo")
    solo_inta = calcular_clima(clima.loc[clima["origen"] == "INTA_verificado", ["date", "Tmax", "Tmin"]], ParametrosClima()).frio.set_index("periodo")

    for anio in (2019, 2020, 2021, 2022):
        assert solo_inta.loc[anio, "Horas_Frio"] == pytest.approx(completo.loc[anio, "Horas_Frio"], abs=1e-9)
        assert solo_inta.loc[anio, "estado_frio"] == completo.loc[anio, "estado_frio"]


def test_t20_los_dias_no_verificados_dentro_de_mayo_a_agosto_son_4_26_y_42_en_2023_2024_y_2025(clima):
    fechas = pd.to_datetime(clima.loc[clima["origen"] == "no_verificado", "date"])
    en_la_ventana = fechas[fechas.dt.month.isin([5, 6, 7, 8])]

    assert en_la_ventana.dt.year.value_counts().sort_index().to_dict() == {2023: 4, 2024: 26, 2025: 42}
