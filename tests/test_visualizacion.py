import pandas as pd
import pytest
from shapely.geometry import box

from kiwitracking.analisis import analizar
from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.visualizacion import (
    COLOR_BAJO_MALLA,
    COLOR_FUERA_DE_MALLA,
    crear_mapa,
    generar_mapa,
    preparar_mapa,
)

POLIGONO = box(-57.8950, -38.2130, -57.8928, -38.2112)


def _plantas():
    return pd.DataFrame(
        {
            "id": [10, 20, 30, 40],
            "X": [-57.8939, -57.8940, -57.9000, -57.8939],
            "Y": [-38.2121, -38.2125, -38.2121, -38.2200],
            "bajo_malla": [1, 1, 0, 0],
        }
    )


def test_rf15_hay_un_punto_por_planta_con_su_id_y_sus_coordenadas():
    datos = preparar_mapa(_plantas(), POLIGONO)

    assert [p.id for p in datos.puntos] == [10, 20, 30, 40]
    assert datos.puntos[0].x == pytest.approx(-57.8939)
    assert datos.puntos[0].y == pytest.approx(-38.2121)


def test_rf15_el_color_depende_de_bajo_malla():
    datos = preparar_mapa(_plantas(), POLIGONO)

    assert [p.color for p in datos.puntos] == [
        COLOR_BAJO_MALLA, COLOR_BAJO_MALLA, COLOR_FUERA_DE_MALLA, COLOR_FUERA_DE_MALLA,
    ]
    assert [p.bajo_malla for p in datos.puntos] == [1, 1, 0, 0]


def test_rf15_los_dos_colores_son_distintos():
    assert COLOR_BAJO_MALLA != COLOR_FUERA_DE_MALLA


def test_rf15_cuenta_las_plantas_de_cada_grupo():
    datos = preparar_mapa(_plantas(), POLIGONO)

    assert (datos.n_bajo_malla, datos.n_fuera_de_malla) == (2, 2)


def test_rf15_incluye_el_poligono_para_superponerlo():
    datos = preparar_mapa(_plantas(), POLIGONO)

    assert datos.poligono.equals(POLIGONO)


def test_rf15_el_poligono_es_opcional():
    datos = preparar_mapa(_plantas(), None)

    assert datos.poligono is None
    assert len(datos.puntos) == 4


def test_rf16_devuelve_la_huella_de_la_tabla():
    plantas = _plantas()

    datos = preparar_mapa(plantas, POLIGONO)

    assert datos.huella == huella(plantas)


def test_rf16_la_huella_del_mapa_sirve_como_confirmacion_en_analizar():
    # Flujo completo: se mira el mapa, se toma su huella y se la pasa al análisis.
    plantas = pd.DataFrame(
        {
            "id": range(1, 13),
            "KVPI_mean": [0.62, 0.60, 0.64, 0.58, 0.66, 0.61, 0.59, 0.63, 0.46, 0.44, 0.48, 0.45],
            "KVPI_std": [0.02, 0.05, 0.02, 0.05, 0.03, 0.04, 0.05, 0.02, 0.03, 0.04, 0.02, 0.05],
            "bajo_malla": [0] * 8 + [1] * 4,
            "X": [-57.90 + 0.0001 * i for i in range(12)],
            "Y": [-38.21] * 12,
        }
    )

    datos = preparar_mapa(plantas, None)
    resultado = analizar(plantas, huella_confirmada=datos.huella, estado_frio_ultima_campana="Adecuado")

    assert resultado.resumen.correccion_aplicada is True
    assert resultado.advertencias == []


@pytest.mark.parametrize("columna", ["id", "bajo_malla", "X", "Y"])
def test_rf15_si_falta_una_columna_necesaria_da_error_que_la_nombra(columna):
    plantas = _plantas().drop(columns=[columna])

    with pytest.raises(ErrorDeEntrada, match=columna):
        preparar_mapa(plantas, POLIGONO)


def test_rf15_las_columnas_de_coordenadas_se_pueden_indicar():
    plantas = _plantas().rename(columns={"X": "lon", "Y": "lat"})

    datos = preparar_mapa(plantas, POLIGONO, columna_x="lon", columna_y="lat")

    assert len(datos.puntos) == 4


def test_rf15_coordenadas_fuera_del_rango_de_longitud_y_latitud_dan_error_que_pide_epsg_4326():
    plantas = _plantas()
    plantas["X"] = [421743.0, 421744.0, 421745.0, 421746.0]  # metros UTM, no grados
    plantas["Y"] = [5770285.0, 5770286.0, 5770287.0, 5770288.0]

    with pytest.raises(ErrorDeEntrada, match="EPSG:4326"):
        preparar_mapa(plantas, POLIGONO)


def test_rf15_una_planta_sin_coordenadas_da_error():
    plantas = _plantas()
    plantas.loc[1, "X"] = float("nan")

    with pytest.raises(ErrorDeEntrada, match="sin coordenadas"):
        preparar_mapa(plantas, POLIGONO)


def test_rf15_bajo_malla_con_valores_distintos_de_0_y_1_da_error():
    plantas = _plantas()
    plantas.loc[0, "bajo_malla"] = 2

    with pytest.raises(ErrorDeEntrada, match="bajo_malla"):
        preparar_mapa(plantas, POLIGONO)


def test_rf15_no_modifica_la_tabla_de_entrada():
    plantas = _plantas()
    copia = plantas.copy()

    preparar_mapa(plantas, POLIGONO)

    pd.testing.assert_frame_equal(plantas, copia)


# --- T22: mapa HTML de verificación -------------------------------------------------------


def _html(tmp_path, plantas=None, poligono=POLIGONO, **kwargs):
    plantas = _plantas() if plantas is None else plantas
    ruta = tmp_path / "mapa.html"
    h = generar_mapa(plantas, poligono, ruta, **kwargs)
    return h, ruta.read_text(encoding="utf-8")


def test_rf15_se_genera_el_archivo_html_y_se_devuelve_la_huella_de_la_tabla(tmp_path):
    plantas = _plantas()

    h, _ = _html(tmp_path, plantas)

    assert (tmp_path / "mapa.html").exists()
    assert h == huella(plantas)


def test_rf15_el_html_tiene_un_marcador_por_planta(tmp_path):
    _, html = _html(tmp_path)

    assert html.count("L.circleMarker(") == 4


def test_rf15_el_html_tiene_los_colores_de_cada_grupo(tmp_path):
    _, html = _html(tmp_path)

    assert COLOR_BAJO_MALLA in html
    assert COLOR_FUERA_DE_MALLA in html


def test_rf15_el_html_incluye_el_poligono_cuando_se_da(tmp_path):
    _, html = _html(tmp_path, poligono=POLIGONO)

    assert html.count("L.geoJson(") == 1


def test_rf15_sin_poligono_el_html_no_lo_incluye_pero_sigue_teniendo_los_marcadores(tmp_path):
    _, html = _html(tmp_path, poligono=None)

    assert html.count("L.geoJson(") == 0
    assert html.count("L.circleMarker(") == 4


def test_rf16_el_mapa_muestra_la_huella_y_las_cantidades_para_que_se_pueda_copiar(tmp_path):
    plantas = _plantas()

    h, html = _html(tmp_path, plantas)

    assert h in html
    assert "2 plantas bajo malla" in html
    assert "2 plantas fuera de malla" in html


def test_rf15_cada_marcador_muestra_el_id_y_el_grupo_al_pasar_el_mouse(tmp_path):
    _, html = _html(tmp_path)

    assert "Planta 10" in html and "bajo malla" in html
    assert "Planta 30" in html and "fuera de malla" in html


def test_rf15_con_fondo_satelital_el_html_pide_las_teselas_de_esri(tmp_path):
    _, html = _html(tmp_path, fondo_satelital=True)

    assert "World_Imagery" in html


def test_rf15_sin_fondo_satelital_no_hay_pedidos_a_servicios_de_mapas(tmp_path):
    _, html = _html(tmp_path, fondo_satelital=False)

    assert "arcgisonline" not in html
    assert "tile.openstreetmap" not in html


def test_rf15_crea_las_carpetas_que_falten(tmp_path):
    ruta = tmp_path / "resultados" / "verificacion" / "mapa.html"

    generar_mapa(_plantas(), POLIGONO, ruta)

    assert ruta.exists()


def test_rf15_el_mapa_se_centra_en_las_plantas():
    datos = preparar_mapa(_plantas(), POLIGONO)

    mapa = crear_mapa(datos)

    latitud, longitud = mapa.location
    assert -38.2200 <= latitud <= -38.2121
    assert -57.9000 <= longitud <= -57.8939


def test_rf15_los_errores_de_las_coordenadas_llegan_hasta_generar_mapa(tmp_path):
    plantas = _plantas()
    plantas["X"] = [421743.0, 421744.0, 421745.0, 421746.0]
    plantas["Y"] = [5770285.0, 5770286.0, 5770287.0, 5770288.0]

    with pytest.raises(ErrorDeEntrada, match="EPSG:4326"):
        generar_mapa(plantas, POLIGONO, tmp_path / "mapa.html")

    assert not (tmp_path / "mapa.html").exists()


def test_rf15_generar_mapa_no_modifica_la_tabla_de_entrada(tmp_path):
    plantas = _plantas()
    copia = plantas.copy()

    generar_mapa(plantas, POLIGONO, tmp_path / "mapa.html")

    pd.testing.assert_frame_equal(plantas, copia)


# --- T34 (Cambio 4): id duplicados en el mapa de verificación -----------------------------


def _plantas_con_repetida():
    return pd.concat([_plantas(), _plantas().iloc[[0]]], ignore_index=True)  # la planta 10 (bajo malla), dos veces


def test_rf29_el_mapa_dibuja_una_sola_vez_la_planta_repetida_y_avisa():
    datos = preparar_mapa(_plantas_con_repetida(), POLIGONO)

    assert [p.id for p in datos.puntos] == [10, 20, 30, 40]
    assert (datos.n_bajo_malla, datos.n_fuera_de_malla) == (2, 2)
    assert [a.codigo for a in datos.advertencias] == ["ID_DUPLICADO"]


def test_rf16_la_huella_del_mapa_no_cambia_por_la_fila_repetida():
    assert preparar_mapa(_plantas_con_repetida(), POLIGONO).huella == huella(_plantas())


def test_rf29_sin_repetidas_el_mapa_no_trae_advertencias():
    assert preparar_mapa(_plantas(), POLIGONO).advertencias == []


def test_rf30_un_id_repetido_con_otra_posicion_es_un_error_en_el_mapa():
    plantas = pd.concat([_plantas(), _plantas().iloc[[0]].assign(X=-57.0)], ignore_index=True)

    with pytest.raises(ErrorDeEntrada, match="id repetidos"):
        preparar_mapa(plantas, POLIGONO)


def test_rf29_el_html_tiene_un_marcador_por_planta_y_dice_que_se_descartaron_filas(tmp_path):
    ruta = tmp_path / "mapa.html"

    generar_mapa(_plantas_con_repetida(), POLIGONO, ruta)

    html = ruta.read_text(encoding="utf-8")
    assert html.count("L.circleMarker(") == 4
    assert "filas repetidas" in html
