"""El flujo completo `mapa` → `analizar` con el lote y el clima reales (spec 003, criterios 2 a 5 y 7).

Todo pasa por `main(argv)`, como lo haría la línea de comandos. Las horas de frío de 2024 y 2025 dependen de
días interpolados (ver `AGENTS.md`).
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import shapely
from pyproj import Transformer
from shapely.geometry import mapping

from kiwitracking.cli import main
from kiwitracking.huella import huella
from kiwitracking.io import leer_poligono_geojson

GOLDEN = Path(__file__).parent / "golden"
PLANTAS = GOLDEN / "datos_plantas_completos.csv"
MALLA = GOLDEN / "malla_zona.geojson"
CLIMA = GOLDEN / "clima_diario.csv"
POSGAR = "EPSG:22185"


def _mapa(carpeta, capsys, plantas=PLANTAS, malla=MALLA, crs="EPSG:4326", nombre="mapa.html"):
    codigo = main(["mapa", "--plantas", str(plantas), "--malla", str(malla), "--crs-plantas", crs, "--salida", str(carpeta / nombre), "--sin-fondo-satelital"])
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    return salida


def _huella_de(salida):
    return re.search(r"^Huella: ([0-9a-f]{12})$", salida, re.M).group(1)


def _analizar(carpeta, capsys, huella_indicada, *extra, plantas=PLANTAS, malla=MALLA, crs="EPSG:4326", destino="resultados"):
    codigo = main(
        ["analizar", "--plantas", str(plantas), "--malla", str(malla), "--crs-plantas", crs, "--huella", huella_indicada,
         "--salida", str(carpeta / destino), *extra]
    )
    capsys.readouterr()
    return codigo


def _json(carpeta, nombre, destino="resultados"):
    return json.loads((carpeta / destino / nombre).read_text(encoding="utf-8"))


@pytest.fixture
def lote():
    return pd.read_csv(PLANTAS, encoding="utf-8")


# --- Criterio 2: el mapa -----------------------------------------------------------------------------------


def test_criterio2_el_mapa_informa_53_plantas_bajo_malla_106_fuera_y_la_huella_del_lote(tmp_path, capsys, lote):
    salida = _mapa(tmp_path, capsys)

    assert re.search(r"bajo malla: 53\b", salida) and re.search(r"fuera de malla: 106\b", salida)
    assert _huella_de(salida) == huella(lote)


# --- Criterio 3: el flujo completo con clima ------------------------------------------------------------------


def test_criterio3_mapa_y_luego_analizar_con_clima_y_campana_2024_da_16_mantener_y_19_intervenir(tmp_path, capsys):
    huella_del_mapa = _huella_de(_mapa(tmp_path, capsys))

    codigo = _analizar(tmp_path, capsys, huella_del_mapa, "--clima", str(CLIMA), "--campana", "2024")

    assert codigo == 0
    recomendaciones = pd.read_csv(tmp_path / "resultados" / "plantas.csv", encoding="utf-8")["recomendacion"].value_counts().to_dict()
    assert (recomendaciones["Mantener"], recomendaciones["Intervenir"]) == (16, 19)
    resumen = _json(tmp_path, "resumen.json")
    assert resumen["huella"] == huella_del_mapa
    assert resumen["estado_frio"]["origen"] == "clima" and resumen["estado_frio"]["estado"] == "Óptimo"
    assert resumen["estado_frio"]["periodo"] == 2024 and resumen["estado_frio"]["horas"] == pytest.approx(1128.8, abs=0.05)
    assert "CAMPANA_NO_INDICADA" not in [a["codigo"] for a in _json(tmp_path, "advertencias.json")]


def test_criterio3_sin_campana_el_estado_es_adecuado_de_2025_y_advertencias_trae_campana_no_indicada(tmp_path, capsys):
    huella_del_mapa = _huella_de(_mapa(tmp_path, capsys))

    codigo = _analizar(tmp_path, capsys, huella_del_mapa, "--clima", str(CLIMA))

    assert codigo == 0
    estado = _json(tmp_path, "resumen.json")["estado_frio"]
    assert (estado["estado"], estado["periodo"]) == ("Adecuado", 2025)
    assert estado["cobertura"] == pytest.approx(119 / 123) and estado["hueco_maximo"] == 4
    assert "CAMPANA_NO_INDICADA" in [a["codigo"] for a in _json(tmp_path, "advertencias.json")]
    recomendaciones = pd.read_csv(tmp_path / "resultados" / "plantas.csv", encoding="utf-8")["recomendacion"].value_counts().to_dict()
    assert (recomendaciones["Mantener"], recomendaciones["Intervenir"]) == (16, 19)


def test_criterio3_el_resumen_registra_los_parametros_de_clima_usados(tmp_path, capsys):
    huella_del_mapa = _huella_de(_mapa(tmp_path, capsys))

    _analizar(tmp_path, capsys, huella_del_mapa, "--clima", str(CLIMA), "--campana", "2024", "--cobertura-minima", "0.8")

    assert _json(tmp_path, "resumen.json")["parametros"]["clima"] == {
        "ventana_frio": "invierno", "formato_fecha": None, "cobertura_minima": 0.8, "max_hueco_dias": 7, "campana": 2024,
    }


# --- Criterio 4: reproduce lo publicado -----------------------------------------------------------------------


def test_criterio4_con_no_escalar_std_y_frio_deficiente_plantas_csv_reproduce_los_resultados_publicados(tmp_path, capsys, lote):
    huella_del_mapa = _huella_de(_mapa(tmp_path, capsys))

    codigo = _analizar(tmp_path, capsys, huella_del_mapa, "--no-escalar-std", "--estado-frio", "Deficiente")

    assert codigo == 0
    resultado = pd.read_csv(tmp_path / "resultados" / "plantas.csv", encoding="utf-8").set_index("id")
    publicado = lote.set_index("id")
    assert (resultado["KVPI_corregido"] - publicado["KVPI_corregido"]).abs().max() < 1e-9
    assert resultado["ambiente"].tolist() == publicado["ambiente"].tolist()
    assert resultado["recomendacion"].tolist() == publicado["recomendacion"].tolist()
    cuentas = resultado["recomendacion"].value_counts().to_dict()
    assert cuentas.get("Mantener", 0) == 0 and cuentas["Intervenir"] == 19
    assert _json(tmp_path, "resumen.json")["resumen"]["escalar_std"] is False


# --- Criterio 5: el control de la huella ------------------------------------------------------------------------


@pytest.mark.parametrize("modo", ["auto", "forzar"])
def test_criterio5_una_huella_incorrecta_da_codigo_1_incluso_con_forzar_y_no_escribe_nada(tmp_path, capsys, modo):
    codigo = main(
        ["analizar", "--plantas", str(PLANTAS), "--malla", str(MALLA), "--crs-plantas", "EPSG:4326", "--huella", "000000000000",
         "--correccion", modo, "--estado-frio", "Adecuado", "--salida", str(tmp_path / "resultados")]
    )

    err = capsys.readouterr().err
    assert codigo == 1 and "no corresponde" in err
    assert not (tmp_path / "resultados").exists()


def test_criterio5_la_huella_de_otro_lote_tampoco_sirve(tmp_path, capsys, lote):
    otra = huella(lote.assign(bajo_malla=1 - lote["bajo_malla"]))  # un lote distinto: el conjunto bajo malla cambia

    codigo = _analizar(tmp_path, capsys, otra, "--estado-frio", "Adecuado")

    assert codigo == 1 and not (tmp_path / "resultados").exists()


# --- Criterio 7: el mismo lote en otro sistema de coordenadas -----------------------------------------------------


def _a_posgar(carpeta):
    """El lote y la malla de referencia en EPSG:22185 (metros), con la malla declarada en ese sistema."""
    ida = Transformer.from_crs("EPSG:4326", POSGAR, always_xy=True)
    lote = pd.read_csv(PLANTAS, encoding="utf-8")
    x, y = ida.transform(lote["X"].to_numpy(), lote["Y"].to_numpy())
    plantas = carpeta / "plantas_posgar.csv"
    lote.drop(columns=["bajo_malla"]).assign(X=x, Y=y).to_csv(plantas, index=False)

    poligono, _ = leer_poligono_geojson(MALLA)
    en_metros = shapely.transform(poligono, lambda c: np.column_stack(ida.transform(c[:, 0], c[:, 1])))
    malla = carpeta / "malla_posgar.geojson"
    malla.write_text(
        json.dumps({
            "type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": POSGAR}},
            "features": [{"type": "Feature", "properties": {}, "geometry": mapping(en_metros)}],
        }),
        encoding="utf-8",
    )
    return plantas, malla


def _pares(ruta_html):
    html = ruta_html.read_text(encoding="utf-8")
    return np.array([(float(a), float(b)) for a, b in re.findall(r"\[(-?\d+\.\d+), (-?\d+\.\d+)\]", html)])


def test_criterio7_el_lote_en_otro_sistema_da_las_mismas_plantas_bajo_malla_la_misma_huella_y_el_mismo_dibujo(tmp_path, capsys):
    plantas, malla = _a_posgar(tmp_path)

    original = _mapa(tmp_path, capsys, nombre="original.html")
    convertido = _mapa(tmp_path, capsys, plantas=plantas, malla=malla, crs=POSGAR, nombre="convertido.html")

    assert re.search(r"bajo malla: 53\b", convertido) and re.search(r"fuera de malla: 106\b", convertido)
    assert _huella_de(convertido) == _huella_de(original)
    a, b = _pares(tmp_path / "original.html"), _pares(tmp_path / "convertido.html")
    assert a.shape == b.shape and a.shape[0] >= 159  # las plantas y los vértices del polígono
    assert np.abs(a - b).max() < 1e-6


def test_criterio7_analizar_en_otro_sistema_da_el_mismo_resultado_que_en_el_original(tmp_path, capsys):
    plantas, malla = _a_posgar(tmp_path)
    huella_del_mapa = _huella_de(_mapa(tmp_path, capsys, plantas=plantas, malla=malla, crs=POSGAR))

    codigo = _analizar(tmp_path, capsys, huella_del_mapa, "--estado-frio", "Adecuado", plantas=plantas, malla=malla, crs=POSGAR)

    assert codigo == 0
    recomendaciones = pd.read_csv(tmp_path / "resultados" / "plantas.csv", encoding="utf-8")["recomendacion"].value_counts().to_dict()
    assert (recomendaciones["Mantener"], recomendaciones["Intervenir"]) == (16, 19)


def test_criterio7_plantas_en_metros_con_la_malla_en_grados_se_cruzan_cada_una_desde_su_sistema(tmp_path, capsys):
    plantas, _ = _a_posgar(tmp_path)  # plantas en EPSG:22185; la malla original sigue en grados (CRS84)

    salida = _mapa(tmp_path, capsys, plantas=plantas, malla=MALLA, crs=POSGAR)

    assert re.search(r"bajo malla: 53\b", salida) and re.search(r"fuera de malla: 106\b", salida)
    assert _huella_de(salida) == _huella_de(_mapa(tmp_path, capsys, nombre="original.html"))
