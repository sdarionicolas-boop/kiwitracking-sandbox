"""Ventana de frío "invierno" (por defecto) con el clima real del lote de referencia (spec 002, criterios 3 y 4).

Mayo a agosto de un mismo año calendario (123 días). Las horas de 2024 y 2025 dependen de días no
verificados contra INTA: ver `AGENTS.md` y `test_clima_procedencia.py`.
"""

from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.clima import calcular_clima
from kiwitracking.clima_parametros import ParametrosClima

ARCHIVO = Path(__file__).parent / "golden" / "clima_diario.csv"
HORAS = {2019: 956.5, 2020: 853.5, 2021: 925.0, 2022: 1090.4, 2023: 853.5, 2024: 1128.8, 2025: 834.2}
ESTADOS = {2019: "Óptimo", 2020: "Adecuado", 2021: "Adecuado", 2022: "Óptimo", 2023: "Adecuado", 2024: "Óptimo", 2025: "Adecuado"}


@pytest.fixture(scope="module")
def frio():
    clima = pd.read_csv(ARCHIVO, encoding="utf-8")[["date", "Tmax", "Tmin"]]
    return calcular_clima(clima, ParametrosClima()).frio.set_index("periodo")


def test_criterio3_las_ventanas_son_los_7_inviernos_de_2019_a_2025(frio):
    assert frio.index.tolist() == list(range(2019, 2026))


def test_criterio3_las_horas_de_frio_de_cada_invierno_coinciden_con_las_esperadas(frio):
    for anio, horas in HORAS.items():
        assert frio.loc[anio, "Horas_Frio"] == pytest.approx(horas, abs=0.05), anio


def test_criterio3_cada_invierno_tiene_123_dias_esperados_y_2025_tiene_119_disponibles(frio):
    assert (frio["dias_esperados"] == 123).all()
    assert (frio.loc[2019:2024, "dias_disponibles"] == 123).all()
    assert frio.loc[2025, "dias_disponibles"] == 119


def test_criterio3_todos_los_inviernos_son_clasificables(frio):
    assert frio["completo"].all()


def test_criterio4_los_estados_son_los_esperados_y_ninguno_es_deficiente(frio):
    assert frio["estado_frio"].to_dict() == ESTADOS
    assert "Deficiente" not in frio["estado_frio"].tolist()


def test_criterio4_los_dos_deficiente_del_notebook_ya_no_aparecen_en_modo_invierno(frio):
    # El "Deficiente" de 2018 y de 2025 en el notebook venía de mezclar dos inviernos recortados.
    assert 2018 not in frio.index
    assert frio.loc[2025, "estado_frio"] == "Adecuado"
