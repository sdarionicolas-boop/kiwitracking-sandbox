import json

import numpy as np
import pandas as pd
import pytest
import shapely
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, box

from kiwitracking.io import calcular_bajo_malla, cruzar_con_malla, leer_csv, leer_poligono_geojson
from kiwitracking.resultado import ErrorDeEntrada

CONTENIDO = "temporada,estado_frio\n2019,Adecuado\n2021,Óptimo\n"


def _escribir(ruta, texto, codificacion):
    ruta.write_bytes(texto.encode(codificacion))
    return ruta


def test_rf3_lee_un_csv_utf8_con_tildes(tmp_path):
    ruta = _escribir(tmp_path / "frio.csv", CONTENIDO, "utf-8")

    tabla = leer_csv(ruta)

    assert list(tabla.columns) == ["temporada", "estado_frio"]
    assert tabla["estado_frio"].tolist() == ["Adecuado", "Óptimo"]


def test_rf3_lee_un_csv_solo_ascii(tmp_path):
    ruta = _escribir(tmp_path / "plantas.csv", "id,KVPI_mean\n1,0.5\n2,0.6\n", "utf-8")

    tabla = leer_csv(ruta)

    assert tabla["KVPI_mean"].tolist() == [0.5, 0.6]


def test_rf3_un_csv_en_windows_1252_con_tildes_da_error_que_menciona_utf8(tmp_path):
    ruta = _escribir(tmp_path / "frio.csv", CONTENIDO, "cp1252")

    with pytest.raises(ErrorDeEntrada, match="UTF-8"):
        leer_csv(ruta)


def test_rf3_el_error_de_codificacion_nombra_el_archivo(tmp_path):
    ruta = _escribir(tmp_path / "frio_roto.csv", CONTENIDO, "cp1252")

    with pytest.raises(ErrorDeEntrada, match="frio_roto.csv"):
        leer_csv(ruta)


def test_rf3_un_csv_utf8_con_bom_de_excel_no_contamina_el_nombre_de_la_primera_columna(tmp_path):
    ruta = _escribir(tmp_path / "bom.csv", "﻿" + CONTENIDO, "utf-8")

    tabla = leer_csv(ruta)

    assert list(tabla.columns) == ["temporada", "estado_frio"]


def test_rf3_un_archivo_inexistente_sigue_siendo_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        leer_csv(tmp_path / "no_existe.csv")


def test_rf3_devuelve_un_dataframe(tmp_path):
    ruta = _escribir(tmp_path / "frio.csv", CONTENIDO, "utf-8")

    assert isinstance(leer_csv(ruta), pd.DataFrame)



# --- T18: texto corrupto en columnas de categorías --------------------------------------


def _csv_utf8(tmp_path, texto, nombre="datos.csv"):
    return _escribir(tmp_path / nombre, texto, "utf-8")


def test_rf4_texto_corrupto_en_una_columna_de_categorias_da_error_que_nombra_columna_y_valor(tmp_path):
    ruta = _csv_utf8(tmp_path, "temporada,estado_frio\n2021,Ã“ptimo\n")

    with pytest.raises(ErrorDeEntrada) as error:
        leer_csv(ruta)

    assert "estado_frio" in str(error.value)
    assert "Ã“ptimo" in str(error.value)


@pytest.mark.parametrize("corrupto", ["Ã“ptimo", "Â°C", "â€œcomillasâ€"])
def test_rf4_detecta_las_tres_secuencias_tipicas(tmp_path, corrupto):
    ruta = _csv_utf8(tmp_path, f"id,ambiente\n1,{corrupto}\n")

    with pytest.raises(ErrorDeEntrada, match="ambiente"):
        leer_csv(ruta)


@pytest.mark.parametrize("columna", ["ambiente", "recomendacion", "estado_frio", "estado_frio_ultima_campana"])
def test_rf4_revisa_las_cuatro_columnas_de_categorias(tmp_path, columna):
    ruta = _csv_utf8(tmp_path, f"id,{columna}\n1,Ã“ptimo\n")

    with pytest.raises(ErrorDeEntrada, match=columna):
        leer_csv(ruta)


def test_rf4_el_mismo_texto_en_otra_columna_no_da_error(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,comentario\n1,Ã“ptimo\n")

    tabla = leer_csv(ruta)

    assert tabla["comentario"].tolist() == ["Ã“ptimo"]


def test_rf4_categorias_bien_escritas_con_tildes_no_dan_error(tmp_path):
    ruta = _csv_utf8(tmp_path, "temporada,estado_frio\n2019,Adecuado\n2021,Óptimo\n2018,Deficiente\n")

    tabla = leer_csv(ruta)

    assert tabla["estado_frio"].tolist() == ["Adecuado", "Óptimo", "Deficiente"]


def test_rf4_los_valores_vacios_en_una_columna_de_categorias_no_dan_error(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,recomendacion\n1,Mantener\n2,\n")

    tabla = leer_csv(ruta)

    assert len(tabla) == 2


def test_rf4_el_error_nombra_el_archivo(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,ambiente\n1,Ã“ptimo\n", nombre="resultados.csv")

    with pytest.raises(ErrorDeEntrada, match="resultados.csv"):
        leer_csv(ruta)


def test_rf4_un_archivo_sin_columnas_de_categorias_no_se_revisa(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,KVPI_mean\n1,0.5\n")

    assert len(leer_csv(ruta)) == 1


# --- T19: cruce punto-en-polígono con sistema de coordenadas ----------------------------


def _cuadrado(x0=0.0, y0=0.0, x1=10.0, y1=10.0):
    return box(x0, y0, x1, y1)


def _plantas(puntos, indice=None):
    return pd.DataFrame({"id": range(1, len(puntos) + 1), "X": [p[0] for p in puntos], "Y": [p[1] for p in puntos]}, index=indice)


def test_rf17_marca_1_las_plantas_dentro_del_poligono_y_0_las_de_afuera():
    plantas = _plantas([(1, 1), (9, 9), (11, 5), (-1, -1)])

    bajo_malla = calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [1, 1, 0, 0]


def test_rf17_devuelve_una_serie_de_enteros_alineada_con_el_indice_y_llamada_bajo_malla():
    plantas = _plantas([(1, 1), (11, 5)], indice=[40, 7])

    bajo_malla = calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.name == "bajo_malla"
    assert bajo_malla.index.tolist() == [40, 7]
    assert pd.api.types.is_integer_dtype(bajo_malla)


def test_rf17_una_planta_justo_en_el_borde_cuenta_como_dentro():
    plantas = _plantas([(0, 5), (10, 10)])

    bajo_malla = calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [1, 1]


def test_rf17_funciona_con_un_poligono_de_varias_partes():
    dos_partes = MultiPolygon([_cuadrado(0, 0, 2, 2), _cuadrado(10, 10, 12, 12)])
    plantas = _plantas([(1, 1), (5, 5), (11, 11)])

    bajo_malla = calcular_bajo_malla(plantas, dos_partes, "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [1, 0, 1]


@pytest.mark.parametrize("crs_plantas,crs_poligono", [(None, "EPSG:4326"), ("EPSG:4326", None), ("", "EPSG:4326"), ("EPSG:4326", "  ")])
def test_rf18_si_falta_declarar_un_sistema_de_coordenadas_da_error(crs_plantas, crs_poligono):
    plantas = _plantas([(1, 1)])

    with pytest.raises(ErrorDeEntrada, match="sistema de coordenadas"):
        calcular_bajo_malla(plantas, _cuadrado(), crs_plantas, crs_poligono)


def _lonlat_a_utm(poligono_lonlat):
    transformador = Transformer.from_crs("EPSG:4326", "EPSG:32721", always_xy=True)
    return shapely.transform(
        poligono_lonlat, lambda c: np.column_stack(transformador.transform(c[:, 0], c[:, 1]))
    )


# Un lote cerca de Miramar (lon, lat): el polígono es un rectángulo de unos 200 m x 200 m.
LOTE_LONLAT = box(-57.8950, -38.2130, -57.8928, -38.2112)
PUNTOS_LONLAT = [(-57.8939, -38.2121), (-57.8940, -38.2125), (-57.9000, -38.2121), (-57.8939, -38.2200)]  # dentro, dentro, fuera, fuera


def test_rf18_con_poligono_en_utm_y_plantas_en_lonlat_da_lo_mismo_que_con_ambos_en_lonlat():
    plantas = _plantas(PUNTOS_LONLAT)
    referencia = calcular_bajo_malla(plantas, LOTE_LONLAT, "EPSG:4326", "EPSG:4326")
    assert referencia.tolist() == [1, 1, 0, 0]  # la referencia es válida

    resultado = calcular_bajo_malla(plantas, _lonlat_a_utm(LOTE_LONLAT), "EPSG:4326", "EPSG:32721")

    assert resultado.tolist() == referencia.tolist()


def test_rf18_con_plantas_en_utm_y_poligono_en_lonlat_da_lo_mismo_que_con_ambos_en_lonlat():
    transformador = Transformer.from_crs("EPSG:4326", "EPSG:32721", always_xy=True)
    puntos_utm = [transformador.transform(x, y) for x, y in PUNTOS_LONLAT]

    resultado = calcular_bajo_malla(_plantas(puntos_utm), LOTE_LONLAT, "EPSG:32721", "EPSG:4326")

    assert resultado.tolist() == [1, 1, 0, 0]


def test_rf18_si_no_se_convirtiera_el_resultado_seria_distinto():
    # Control negativo: cruzar coordenadas de sistemas distintos como si fueran iguales no da lo mismo.
    plantas = _plantas(PUNTOS_LONLAT)

    mal_cruzado = calcular_bajo_malla(plantas, _lonlat_a_utm(LOTE_LONLAT), "EPSG:4326", "EPSG:4326")

    assert mal_cruzado.tolist() != [1, 1, 0, 0]


def test_rf17_faltan_las_columnas_de_coordenadas_da_error_que_las_nombra():
    plantas = pd.DataFrame({"id": [1], "lon": [1.0]})

    with pytest.raises(ErrorDeEntrada, match="X.*Y"):
        calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")


def test_rf17_las_columnas_de_coordenadas_se_pueden_indicar():
    plantas = pd.DataFrame({"id": [1, 2], "lon": [1.0, 11.0], "lat": [1.0, 5.0]})

    bajo_malla = calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326", columna_x="lon", columna_y="lat")

    assert bajo_malla.tolist() == [1, 0]


def test_rf17_una_planta_sin_coordenadas_da_error_en_lugar_de_contarse_como_fuera_de_malla():
    plantas = _plantas([(1, 1), (float("nan"), 5)])

    with pytest.raises(ErrorDeEntrada, match="sin coordenadas"):
        calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")


def test_rf17_no_modifica_la_tabla_de_plantas():
    plantas = _plantas([(1, 1), (11, 5)])
    copia = plantas.copy()

    calcular_bajo_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    pd.testing.assert_frame_equal(plantas, copia)


# --- T20: advertencia por cruce sospechoso y lectura del polígono -----------------------


def test_rf19_un_cruce_normal_no_da_advertencias():
    plantas = _plantas([(1, 1), (11, 5)])

    bajo_malla, advertencias = cruzar_con_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [1, 0]
    assert advertencias == []


def test_rf19_si_ninguna_planta_cae_en_un_poligono_no_vacio_se_avisa_de_posible_error_de_coordenadas():
    plantas = _plantas([(50, 50), (60, 60)])

    bajo_malla, advertencias = cruzar_con_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [0, 0]  # el resultado igual se devuelve
    assert [a.codigo for a in advertencias] == ["POSIBLE_ERROR_COORDENADAS"]


def test_rf19_si_todas_las_plantas_caen_dentro_tambien_se_avisa():
    plantas = _plantas([(1, 1), (2, 2), (3, 3)])

    bajo_malla, advertencias = cruzar_con_malla(plantas, _cuadrado(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [1, 1, 1]
    assert [a.codigo for a in advertencias] == ["POSIBLE_ERROR_COORDENADAS"]


def test_rf19_con_un_poligono_vacio_no_hay_advertencia_porque_un_lote_sin_malla_es_legitimo():
    plantas = _plantas([(1, 1), (2, 2)])

    bajo_malla, advertencias = cruzar_con_malla(plantas, Polygon(), "EPSG:4326", "EPSG:4326")

    assert bajo_malla.tolist() == [0, 0]
    assert advertencias == []


def test_rf19_declarar_mal_el_sistema_de_coordenadas_se_detecta_por_la_advertencia():
    # Las plantas están en UTM pero se declaran como lon/lat: el cruce da todo 0 y debe avisar.
    transformador = Transformer.from_crs("EPSG:4326", "EPSG:32721", always_xy=True)
    plantas = _plantas([transformador.transform(x, y) for x, y in PUNTOS_LONLAT])

    bajo_malla, advertencias = cruzar_con_malla(plantas, LOTE_LONLAT, "EPSG:4326", "EPSG:4326")

    assert bajo_malla.sum() == 0
    assert [a.codigo for a in advertencias] == ["POSIBLE_ERROR_COORDENADAS"]


def test_rf18_cruzar_con_malla_tambien_exige_declarar_los_sistemas_de_coordenadas():
    with pytest.raises(ErrorDeEntrada, match="sistema de coordenadas"):
        cruzar_con_malla(_plantas([(1, 1)]), _cuadrado(), None, "EPSG:4326")


def _geojson(tmp_path, contenido, nombre="malla.geojson"):
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ruta


CUADRADO_GEOJSON = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}


def test_rf17_lee_un_geojson_con_su_sistema_de_coordenadas_declarado(tmp_path):
    contenido = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [{"type": "Feature", "properties": {}, "geometry": CUADRADO_GEOJSON}],
    }

    poligono, crs = leer_poligono_geojson(_geojson(tmp_path, contenido))

    assert poligono.equals(box(0, 0, 10, 10))
    assert "CRS84" in crs


def test_rf17_un_geojson_sin_crs_se_toma_como_wgs84_segun_el_estandar(tmp_path):
    contenido = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": CUADRADO_GEOJSON}]}

    _, crs = leer_poligono_geojson(_geojson(tmp_path, contenido))

    assert crs == "EPSG:4326"


def test_rf17_con_varios_poligonos_los_une_en_uno_solo(tmp_path):
    otro = {"type": "Polygon", "coordinates": [[[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]]}
    contenido = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": CUADRADO_GEOJSON},
            {"type": "Feature", "properties": {}, "geometry": otro},
        ],
    }

    poligono, _ = leer_poligono_geojson(_geojson(tmp_path, contenido))

    assert poligono.area == pytest.approx(200.0)


def test_rf17_acepta_un_feature_suelto_y_una_geometria_suelta(tmp_path):
    feature = {"type": "Feature", "properties": {}, "geometry": CUADRADO_GEOJSON}

    assert leer_poligono_geojson(_geojson(tmp_path, feature, "a.geojson"))[0].area == pytest.approx(100.0)
    assert leer_poligono_geojson(_geojson(tmp_path, CUADRADO_GEOJSON, "b.geojson"))[0].area == pytest.approx(100.0)


def test_rf17_un_geojson_sin_poligonos_da_error(tmp_path):
    contenido = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [1, 1]}}]}

    with pytest.raises(ErrorDeEntrada, match="polígono"):
        leer_poligono_geojson(_geojson(tmp_path, contenido))


def test_rf17_un_archivo_que_no_es_json_da_error_que_nombra_el_archivo(tmp_path):
    ruta = tmp_path / "roto.geojson"
    ruta.write_text("esto no es json", encoding="utf-8")

    with pytest.raises(ErrorDeEntrada, match="roto.geojson"):
        leer_poligono_geojson(ruta)
