"""Conversión a EPSG:4326 para dibujar el mapa (spec 003, RF-23)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import shapely
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, box

from kiwitracking.huella import huella
from kiwitracking.io import a_wgs84, leer_poligono_geojson
from kiwitracking.resultado import ErrorDeEntrada

GOLDEN = Path(__file__).parent / "golden"
POSGAR = "EPSG:22185"  # POSGAR 94 / Argentina 5: cubre el lote de referencia


@pytest.fixture(scope="module")
def lote():
    return pd.read_csv(GOLDEN / "datos_plantas_completos.csv", encoding="utf-8")[["id", "KVPI_mean", "KVPI_std", "bajo_malla", "X", "Y"]]


@pytest.fixture(scope="module")
def malla():
    poligono, crs = leer_poligono_geojson(GOLDEN / "malla_zona.geojson")
    assert crs == "urn:ogc:def:crs:OGC:1.3:CRS84"  # el GeoJSON sin `crs` es WGS84 con orden longitud-latitud
    return poligono


def _a_posgar(plantas):
    ida = Transformer.from_crs("EPSG:4326", POSGAR, always_xy=True)
    x, y = ida.transform(plantas["X"].to_numpy(), plantas["Y"].to_numpy())
    return plantas.assign(X=x, Y=y)


def _poligono_a_posgar(poligono):
    ida = Transformer.from_crs("EPSG:4326", POSGAR, always_xy=True)
    return shapely.transform(poligono, lambda c: np.column_stack(ida.transform(c[:, 0], c[:, 1])))


def test_rf23_las_plantas_en_un_sistema_proyectado_vuelven_a_longitud_y_latitud(lote):
    proyectadas = _a_posgar(lote)
    assert proyectadas["X"].abs().max() > 1000  # de verdad están en metros, no en grados

    convertidas, _ = a_wgs84(proyectadas, None, POSGAR, None)

    assert (convertidas["X"] - lote["X"]).abs().max() < 1e-6
    assert (convertidas["Y"] - lote["Y"]).abs().max() < 1e-6


def test_rf23_el_poligono_en_un_sistema_proyectado_vuelve_a_longitud_y_latitud(lote, malla):
    _, poligono = a_wgs84(lote, _poligono_a_posgar(malla), None, POSGAR)

    assert poligono.equals_exact(malla, tolerance=1e-6)


def test_rf23_plantas_y_poligono_en_sistemas_distintos_se_convierten_cada_uno_desde_el_suyo(lote, malla):
    # plantas proyectadas y polígono en grados
    convertidas, poligono = a_wgs84(_a_posgar(lote), malla, POSGAR, "EPSG:4326")
    assert (convertidas["X"] - lote["X"]).abs().max() < 1e-6 and poligono.equals_exact(malla, tolerance=1e-12)

    # plantas en grados y polígono proyectado
    convertidas, poligono = a_wgs84(lote, _poligono_a_posgar(malla), "EPSG:4326", POSGAR)
    assert (convertidas["X"] == lote["X"]).all() and poligono.equals_exact(malla, tolerance=1e-6)


def test_rf23_si_ya_estan_en_epsg_4326_no_cambian(lote, malla):
    convertidas, poligono = a_wgs84(lote, malla, "EPSG:4326", "EPSG:4326")

    pd.testing.assert_frame_equal(convertidas, lote)
    assert poligono.equals(malla)


def test_rf23_sin_sistema_declarado_se_supone_longitud_y_latitud_y_no_se_convierte(lote, malla):
    convertidas, poligono = a_wgs84(lote, malla, None, None)

    pd.testing.assert_frame_equal(convertidas, lote)
    assert poligono.equals(malla)


def test_rf23_sin_poligono_devuelve_none(lote):
    _, poligono = a_wgs84(lote, None, "EPSG:4326", None)

    assert poligono is None


def test_rf23_devuelve_copias_y_no_modifica_la_tabla_de_entrada(lote):
    proyectadas = _a_posgar(lote)
    antes = proyectadas.copy()

    convertidas, _ = a_wgs84(proyectadas, None, POSGAR, None)

    pd.testing.assert_frame_equal(proyectadas, antes)
    assert convertidas is not proyectadas


def test_rf23_la_conversion_no_cambia_bajo_malla_ni_las_otras_columnas_ni_la_huella(lote):
    convertidas, _ = a_wgs84(_a_posgar(lote), None, POSGAR, None)

    pd.testing.assert_frame_equal(convertidas.drop(columns=["X", "Y"]), lote.drop(columns=["X", "Y"]))
    assert huella(convertidas) == huella(lote)


def test_rf23_un_poligono_con_agujero_y_varias_partes_conserva_su_forma():
    con_agujero = Polygon(shell=[(-58.0, -38.0), (-57.9, -38.0), (-57.9, -37.9), (-58.0, -37.9)], holes=[[(-57.97, -37.97), (-57.93, -37.97), (-57.93, -37.93), (-57.97, -37.93)]])
    varias = MultiPolygon([con_agujero, box(-57.8, -38.0, -57.7, -37.9)])

    _, convertido = a_wgs84(pd.DataFrame({"X": [0.0], "Y": [0.0]}), _poligono_a_posgar(varias), None, POSGAR)

    assert isinstance(convertido, MultiPolygon) and len(convertido.geoms) == 2
    assert convertido.equals_exact(varias, tolerance=1e-6)
    assert len(list(convertido.geoms[0].interiors)) == 1


def test_rf23_una_coordenada_vacia_sigue_vacia_y_no_se_vuelve_infinita(lote):
    proyectadas = _a_posgar(lote).reset_index(drop=True)
    proyectadas.loc[3, "X"] = np.nan

    convertidas, _ = a_wgs84(proyectadas, None, POSGAR, None)

    assert np.isnan(convertidas.loc[3, "X"])
    assert np.isfinite(convertidas.drop(index=3)[["X", "Y"]].to_numpy()).all()
    assert not np.isinf(convertidas[["X", "Y"]].to_numpy()).any()


def test_rf23_usa_los_nombres_de_columna_indicados(lote):
    renombradas = _a_posgar(lote).rename(columns={"X": "este", "Y": "norte"})

    convertidas, _ = a_wgs84(renombradas, None, POSGAR, None, columna_x="este", columna_y="norte")

    assert (convertidas["este"] - lote["X"]).abs().max() < 1e-6
    assert (convertidas["norte"] - lote["Y"]).abs().max() < 1e-6


@pytest.mark.parametrize("crs_plantas, crs_poligono", [("EPSG:99999", None), (None, "no-existe"), ("EPSG:99999", "no-existe")])
def test_rf23_un_sistema_desconocido_da_un_error_que_lo_nombra(lote, malla, crs_plantas, crs_poligono):
    with pytest.raises(ErrorDeEntrada) as error:
        a_wgs84(lote, malla, crs_plantas, crs_poligono)

    desconocido = crs_plantas if crs_plantas == "EPSG:99999" else crs_poligono
    assert desconocido in str(error.value)
