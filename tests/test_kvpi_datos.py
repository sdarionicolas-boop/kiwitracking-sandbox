"""Serie real de KVPI como dato de referencia (T4.0, C12).

Exportada de Google Earth Engine el 24/10/2026 para el lote de referencia. No prueban el software: dejan escrito,
y vigilado por tests, qué trae el archivo `tests/golden/kvpi_serie.csv` (cuántas filas, plantas y campañas, y que
no trae repetidos ni vacíos), para que una exportación futura que cambie algo se vea enseguida.
"""

from pathlib import Path

import pandas as pd
import pytest

GOLDEN = Path(__file__).parent / "golden"
CAMPANAS = ["2019_2020", "2020_2021", "2021_2022", "2022_2023", "2023_2024", "2024_2025"]


@pytest.fixture(scope="module")
def serie():
    return pd.read_csv(GOLDEN / "kvpi_serie.csv", encoding="utf-8")


def test_serie_real_tiene_954_filas_159_plantas_y_6_campanas(serie):
    assert len(serie) == 954
    assert serie["id"].nunique() == 159
    assert sorted(serie["campaña"].unique()) == CAMPANAS


def test_serie_real_no_trae_repetidos_ni_vacios(serie):
    assert not serie.duplicated(["id", "campaña"]).any()
    assert serie["KVPI"].notna().all()


def test_serie_real_tiene_todas_las_plantas_del_lote_publicado(serie):
    publicado = pd.read_csv(GOLDEN / "datos_plantas_completos.csv", encoding="utf-8")
    assert set(serie["id"]) == set(publicado["id"])
    assert (serie.groupby("id").size() == 6).all()
