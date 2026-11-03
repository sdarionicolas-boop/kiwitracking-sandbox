"""Los días estimados del clima real contra lo conocido (spec 005, criterios 3, 4 y 5).

`clima_diario.csv` tiene 58 días interpolados (ver `AGENTS.md`): 4 caen en el invierno 2023, 26 en el de 2024 y
8 en el de 2025; los otros 20 están fuera de los meses de frío. Los números salen del archivo, no de este test.
"""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.campana import estado_frio_de_campana
from kiwitracking.clima import calcular_clima
from kiwitracking.cli import main
from kiwitracking.huella import huella

GOLDEN = Path(__file__).parent / "golden"
PLANTAS, MALLA, CLIMA = GOLDEN / "datos_plantas_completos.csv", GOLDEN / "malla_zona.geojson", GOLDEN / "clima_diario.csv"


@pytest.fixture(scope="module")
def clima():
    return pd.read_csv(CLIMA, encoding="utf-8")


@pytest.fixture(scope="module")
def resultado(clima):
    return calcular_clima(clima)


@pytest.fixture(scope="module")
def clima_sin_origen(tmp_path_factory, clima):
    ruta = tmp_path_factory.mktemp("sin_origen") / "clima_sin_origen.csv"
    clima.drop(columns="origen").to_csv(ruta, index=False)
    return ruta


@pytest.fixture(scope="module")
def huella_del_mapa():
    """La huella que imprime `mapa` para este lote (la spec 003 comprueba que es igual a `huella()` del CSV)."""
    return huella(pd.read_csv(PLANTAS, encoding="utf-8"))


def _analizar(carpeta, huella, clima_ruta, *extra):
    codigo = main(["analizar", "--plantas", str(PLANTAS), "--malla", str(MALLA), "--crs-plantas", "EPSG:4326",
                   "--huella", huella, "--clima", str(clima_ruta), "--salida", str(carpeta), *extra])  # fmt: skip
    assert codigo == 0
    leer = lambda nombre: (carpeta / nombre).read_text(encoding="utf-8")  # noqa: E731
    return json.loads(leer("resumen.json")), json.loads(leer("advertencias.json")), leer("plantas.csv")


# --- Criterio 3: el recuento del clima real -------------------------------------------------------------------


def test_criterio3_el_archivo_tiene_58_dias_interpolados_38_en_los_meses_de_frio(clima):
    interpolados = clima[clima["origen"] == "interpolado"]
    meses = pd.to_datetime(interpolados["date"]).dt.month
    assert len(interpolados) == 58
    assert meses.isin([5, 6, 7, 8]).sum() == 38


def test_criterio3_el_recuento_por_invierno_es_el_del_archivo(resultado, clima):
    por_anio = resultado.estimados.set_index("periodo")
    assert por_anio.loc[2023, "dias_estimados"] == 4
    assert por_anio.loc[2024, "dias_estimados"] == 26
    assert por_anio.loc[2025, "dias_estimados"] == 8
    assert por_anio.loc[2024, "proporcion_estimada"] == pytest.approx(26 / 123)
    assert por_anio.loc[2025, "proporcion_estimada"] == pytest.approx(8 / 119)  # 119 días disponibles
    assert por_anio.loc[[2019, 2020, 2021, 2022], "dias_estimados"].tolist() == [0, 0, 0, 0]
    frio = resultado.frio.set_index("periodo")
    assert frio.loc[2024, "dias_disponibles"] == 123 and frio.loc[2025, "dias_disponibles"] == 119


def test_criterio3_el_estado_de_2024_trae_el_recuento_y_el_aviso(resultado):
    estado = estado_frio_de_campana(resultado, 2024)
    aviso = next(a for a in estado.advertencias if a.codigo == "DIAS_ESTIMADOS")
    assert (estado.dias_estimados, estado.proporcion_estimada) == (26, pytest.approx(26 / 123))
    assert "2024" in aviso.mensaje and "26 de 123" in aviso.mensaje and "21,1 %" in aviso.mensaje


def test_criterio3_analizar_con_campana_2024_trae_el_aviso_y_el_resumen_registra_26(tmp_path, huella_del_mapa):
    resumen, advertencias, _ = _analizar(tmp_path / "r", huella_del_mapa, CLIMA, "--campana", "2024")
    aviso = next(a for a in advertencias if a["codigo"] == "DIAS_ESTIMADOS")
    assert "26 de 123" in aviso["mensaje"] and "21,1 %" in aviso["mensaje"]
    assert resumen["estado_frio"]["dias_estimados"] == 26
    assert resumen["estado_frio"]["proporcion_estimada"] == pytest.approx(26 / 123)
    assert resumen["parametros"]["clima"]["origenes_estimados"] == ["interpolado"]


def test_criterio3_sin_campana_el_aviso_es_el_de_2025(tmp_path, huella_del_mapa):
    resumen, advertencias, _ = _analizar(tmp_path / "r", huella_del_mapa, CLIMA)
    codigos = [a["codigo"] for a in advertencias]
    assert resumen["estado_frio"]["periodo"] == 2025 and resumen["estado_frio"]["dias_estimados"] == 8
    aviso = next(a for a in advertencias if a["codigo"] == "DIAS_ESTIMADOS")
    assert "8 de 119" in aviso["mensaje"] and "6,7 %" in aviso["mensaje"]
    assert codigos[-3:] == ["CAMPANA_NO_INDICADA", "COBERTURA_PARCIAL", "DIAS_ESTIMADOS"]


# --- Criterio 4: nada cambia -----------------------------------------------------------------------------------


def test_criterio4_con_y_sin_la_columna_origen_el_resultado_es_el_mismo(tmp_path, huella_del_mapa, clima_sin_origen):
    con, avisos_con, plantas_con = _analizar(tmp_path / "con", huella_del_mapa, CLIMA, "--campana", "2024")
    sin, avisos_sin, plantas_sin = _analizar(tmp_path / "sin", huella_del_mapa, clima_sin_origen, "--campana", "2024")

    assert plantas_con == plantas_sin  # plantas.csv idéntico, byte a byte
    recomendaciones = pd.read_csv(tmp_path / "con" / "plantas.csv")["recomendacion"].value_counts().to_dict()
    assert (recomendaciones["Mantener"], recomendaciones["Intervenir"]) == (16, 19)
    for clave in ("origen", "estado", "periodo", "horas", "cobertura", "hueco_maximo"):
        assert con["estado_frio"][clave] == sin["estado_frio"][clave]
    assert (con["estado_frio"]["estado"], con["estado_frio"]["periodo"]) == ("Óptimo", 2024)
    assert con["estado_frio"]["horas"] == pytest.approx(1128.8, abs=0.05)
    assert con["resumen"] == sin["resumen"] and con["huella"] == sin["huella"]
    assert [a for a in avisos_con if a["codigo"] != "DIAS_ESTIMADOS"] == avisos_sin


# --- Criterio 5: compatibilidad ---------------------------------------------------------------------------------


def test_criterio5_sin_la_columna_origen_el_resumen_trae_null_y_no_sale_ningun_aviso_nuevo(tmp_path, huella_del_mapa, clima_sin_origen):
    resumen, sin_aviso, _ = _analizar(tmp_path / "sin", huella_del_mapa, clima_sin_origen)
    _, con_aviso, _ = _analizar(tmp_path / "con", huella_del_mapa, CLIMA)

    assert resumen["estado_frio"]["dias_estimados"] is None and resumen["estado_frio"]["proporcion_estimada"] is None
    assert "DIAS_ESTIMADOS" not in [a["codigo"] for a in sin_aviso]
    assert sin_aviso == [a for a in con_aviso if a["codigo"] != "DIAS_ESTIMADOS"]  # las de siempre, sin ninguna nueva
