"""Reproducción de los resultados del notebook 03 con el clima real del lote de referencia (spec 002, criterio 2).

El clima es `tests/golden/clima_diario.csv` (2.604 días; 58 de ellos no están verificados contra INTA: ver
`AGENTS.md` y `test_clima_procedencia.py`). Los resultados de referencia son `gdd_por_campana.csv` y
`horas_frio_por_campana.csv`, producidos por el notebook con ese mismo archivo.
"""

from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.clima import calcular_clima
from kiwitracking.clima_parametros import ParametrosClima

GOLDEN = Path(__file__).parent / "golden"
REPRODUCCION = dict(ventana_frio="temporada", cobertura_minima=0, max_hueco_dias=None)


@pytest.fixture(scope="module")
def clima():
    return pd.read_csv(GOLDEN / "clima_diario.csv", encoding="utf-8")[["date", "Tmax", "Tmin"]]


@pytest.fixture(scope="module")
def gdd_publicado():
    return pd.read_csv(GOLDEN / "gdd_por_campana.csv", encoding="utf-8")


@pytest.fixture(scope="module")
def frio_publicado():
    return pd.read_csv(GOLDEN / "horas_frio_por_campana.csv", encoding="utf-8")


@pytest.fixture(scope="module")
def reproduccion(clima):
    return calcular_clima(clima, ParametrosClima(**REPRODUCCION))


# --- Criterio 2: el modo de reproducción da lo mismo que el notebook ---------------------------


def test_criterio2_las_temporadas_de_gdd_son_las_8_del_notebook_de_2018_a_2025(reproduccion, gdd_publicado):
    assert reproduccion.gdd["temporada"].tolist() == gdd_publicado["temporada"].tolist() == list(range(2018, 2026))


def test_criterio2_el_gdd_por_temporada_coincide_con_el_notebook_con_diferencia_menor_que_1e_9(reproduccion, gdd_publicado):
    diferencia = (reproduccion.gdd["GDD_total"] - gdd_publicado["GDD_total"]).abs().max()

    assert diferencia < 1e-9


def test_criterio2_el_gdd_total_del_periodo_es_14445_como_dice_la_metadata_del_notebook(reproduccion):
    assert reproduccion.gdd["GDD_total"].sum() == pytest.approx(14445.325, abs=1e-6)
    assert round(reproduccion.gdd["GDD_total"].sum()) == 14445  # "GDD total período: 14445 °C día"


def test_criterio2_las_ventanas_de_frio_son_las_8_del_notebook(reproduccion, frio_publicado):
    assert reproduccion.frio["periodo"].tolist() == frio_publicado["temporada"].tolist() == list(range(2018, 2026))


def test_criterio2_las_horas_de_frio_coinciden_con_el_notebook_con_tolerancia_1e_6(reproduccion, frio_publicado):
    esperadas = [331.7, 921.5, 949.8, 1115.2, 839.3, 1009.0, 1036.1, 439.2]

    assert reproduccion.frio["Horas_Frio"].round(1).tolist() == esperadas  # los valores que figuran en la spec
    diferencia = (reproduccion.frio["Horas_Frio"] - frio_publicado["Horas_Frio"]).abs().max()
    assert diferencia < 1e-6


def test_criterio2_los_estados_coinciden_con_el_notebook_incluidos_los_dos_deficiente_de_los_bordes(reproduccion, frio_publicado):
    assert reproduccion.frio["estado_frio"].tolist() == frio_publicado["estado_frio"].tolist()
    assert reproduccion.frio["estado_frio"].tolist() == [
        "Deficiente", "Adecuado", "Adecuado", "Óptimo", "Adecuado", "Óptimo", "Óptimo", "Deficiente",
    ]


def test_criterio2_en_modo_de_reproduccion_toda_ventana_queda_clasificada(reproduccion):
    assert reproduccion.frio["estado_frio"].notna().all()


def test_criterio2_los_dos_deficiente_publicados_son_las_ventanas_truncadas_de_los_bordes(reproduccion):
    frio = reproduccion.frio.set_index("periodo")

    # 2018 solo tiene mayo-junio de 2019 (61 días) y 2025 solo julio-agosto de 2025 (62 días): cobertura ~0,5.
    assert (frio.loc[2018, "dias_disponibles"], frio.loc[2025, "dias_disponibles"]) == (61, 62)
    assert frio.loc[[2018, 2025], "cobertura"].max() < 0.51
    assert (frio.loc[2018, "estado_frio"], frio.loc[2025, "estado_frio"]) == ("Deficiente", "Deficiente")


def test_criterio2_con_las_reglas_por_defecto_esos_dos_deficiente_dejan_de_publicarse_y_el_resto_no_cambia(clima, frio_publicado):
    # Mismo modo "temporada", pero con cobertura mínima 0,9 y hueco máximo 7: las ventanas truncadas no se clasifican.
    frio = calcular_clima(clima, ParametrosClima(ventana_frio="temporada")).frio.set_index("periodo")
    publicado = frio_publicado.set_index("temporada")

    assert frio.loc[[2018, 2025], "estado_frio"].isna().all()
    for anio in range(2019, 2025):
        assert frio.loc[anio, "estado_frio"] == publicado.loc[anio, "estado_frio"]
        assert frio.loc[anio, "Horas_Frio"] == pytest.approx(publicado.loc[anio, "Horas_Frio"], abs=1e-6)


def test_criterio2_relajar_solo_una_de_las_dos_reglas_no_alcanza_para_reproducir(clima):
    solo_cobertura = calcular_clima(clima, ParametrosClima(ventana_frio="temporada", cobertura_minima=0)).frio.set_index("periodo")
    solo_hueco = calcular_clima(clima, ParametrosClima(ventana_frio="temporada", max_hueco_dias=None)).frio.set_index("periodo")

    assert solo_cobertura.loc[[2018, 2025], "estado_frio"].isna().all()
    assert solo_hueco.loc[[2018, 2025], "estado_frio"].isna().all()


def test_criterio2_el_modo_de_reproduccion_no_agrega_avisos_de_entrada(reproduccion):
    # El archivo no tiene fechas repetidas: las advertencias son solo las de los períodos incompletos.
    assert "FECHA_DUPLICADA" not in [a.codigo for a in reproduccion.advertencias]


def test_criterio2_calcular_clima_no_modifica_la_tabla_cargada(clima):
    copia = clima.copy()

    calcular_clima(clima, ParametrosClima(**REPRODUCCION))

    pd.testing.assert_frame_equal(clima, copia)
