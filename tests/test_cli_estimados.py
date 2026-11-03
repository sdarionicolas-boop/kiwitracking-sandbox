"""T5.5: la opción `--origenes-estimados` de `analizar` (RF-10 de la spec 005)."""

import json
import re
from pathlib import Path

import pytest

from kiwitracking.cli import construir_parser, interpretar_analizar, main
from kiwitracking.resultado import ErrorDeEntrada

GOLDEN = Path(__file__).parent / "golden"
PLANTAS, MALLA, CLIMA = GOLDEN / "datos_plantas_completos.csv", GOLDEN / "malla_zona.geojson", GOLDEN / "clima_diario.csv"


def _solicitud(*extra, huella_indicada="c4e55ae105c6"):
    argv = ["analizar", "--plantas", "plantas.csv", "--huella", huella_indicada]
    return interpretar_analizar(construir_parser().parse_args([*argv, *extra]))


def test_rf10_las_etiquetas_se_separan_por_comas_y_llegan_con_el_nombre_del_parametro():
    solicitud = _solicitud("--clima", "clima.csv", "--origenes-estimados", "interpolado,estimado")
    assert solicitud.parametros_clima == {"origenes_estimados": ["interpolado", "estimado"]}


def test_rf10_se_quitan_los_espacios_al_inicio_y_al_final_de_cada_etiqueta():
    solicitud = _solicitud("--clima", "clima.csv", "--origenes-estimados", "  interpolado ,  satelital  ")
    assert solicitud.parametros_clima["origenes_estimados"] == ["interpolado", "satelital"]


def test_rf10_una_sola_etiqueta_es_una_lista_de_un_elemento():
    assert _solicitud("--clima", "c.csv", "--origenes-estimados", "satelital").parametros_clima == {
        "origenes_estimados": ["satelital"]
    }


def test_rf10_sin_indicarla_no_se_pasa_nada_y_se_usa_el_valor_por_defecto_de_parametros_clima():
    assert "origenes_estimados" not in _solicitud("--clima", "clima.csv").parametros_clima


def test_rf10_las_demas_opciones_de_clima_siguen_igual_junto_con_la_nueva():
    solicitud = _solicitud(
        "--clima", "clima.csv", "--campana", "2024", "--cobertura-minima", "0.8", "--origenes-estimados", "a"
    )
    assert solicitud.parametros_clima == {"cobertura_minima": 0.8, "origenes_estimados": ["a"]}
    assert solicitud.campana == 2024


@pytest.mark.parametrize("valor", ["", " ", ",", "a,", ",a", "a,,b", "a, ,b"])
def test_rf10_un_valor_vacio_da_un_error_de_entrada_que_nombra_la_opcion(valor):
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--clima", "clima.csv", "--origenes-estimados", valor)
    assert "--origenes-estimados" in str(error.value)


def test_rf10_sin_clima_da_el_error_de_las_demas_opciones_de_clima():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--origenes-estimados", "interpolado")
    assert "--origenes-estimados" in str(error.value) and "--clima" in str(error.value)


def test_rf10_sin_clima_y_con_estado_frio_da_el_mismo_error():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--origenes-estimados", "interpolado", "--estado-frio", "Adecuado")
    assert "--origenes-estimados" in str(error.value) and "--clima" in str(error.value)


def test_rf10_junto_con_las_otras_opciones_de_clima_sin_clima_las_nombra_a_todas():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--campana", "2024", "--origenes-estimados", "a")
    assert "--campana" in str(error.value) and "--origenes-estimados" in str(error.value)


def test_rf10_clima_y_estado_frio_siguen_siendo_excluyentes():
    with pytest.raises(ErrorDeEntrada, match="excluyentes"):
        _solicitud("--clima", "c.csv", "--estado-frio", "Óptimo", "--origenes-estimados", "a")


def test_rf10_la_opcion_aparece_en_la_ayuda_de_analizar(capsys):
    assert main(["analizar", "--help"]) == 0
    assert "--origenes-estimados" in capsys.readouterr().out


def test_rf10_un_valor_vacio_desde_main_da_codigo_1_sin_traza(tmp_path, capsys):
    argv = ["analizar", "--plantas", str(PLANTAS), "--huella", "c4e55ae105c6", "--clima", str(CLIMA),
            "--origenes-estimados", "a,,b", "--salida", str(tmp_path / "r")]  # fmt: skip
    assert main(argv) == 1
    error = capsys.readouterr().err
    assert error.startswith("Error:") and "--origenes-estimados" in error and "Traceback" not in error
    assert not (tmp_path / "r").exists()


def test_rf10_sin_clima_desde_main_da_codigo_1(tmp_path, capsys):
    argv = ["analizar", "--plantas", str(PLANTAS), "--huella", "c4e55ae105c6", "--origenes-estimados", "a",
            "--estado-frio", "Adecuado", "--salida", str(tmp_path / "r")]  # fmt: skip
    assert main(argv) == 1
    assert "--origenes-estimados" in capsys.readouterr().err


# --- de punta a punta: la opción llega al recuento --------------------------------------------------------------


def _huella_del_mapa(tmp_path, capsys):
    codigo = main(["mapa", "--plantas", str(PLANTAS), "--malla", str(MALLA), "--crs-plantas", "EPSG:4326",
                   "--salida", str(tmp_path / "mapa.html"), "--sin-fondo-satelital"])  # fmt: skip
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    return re.search(r"^Huella: ([0-9a-f]{12})$", salida, re.M).group(1)


def _analizar(tmp_path, capsys, huella, destino, *extra):
    codigo = main(["analizar", "--plantas", str(PLANTAS), "--malla", str(MALLA), "--crs-plantas", "EPSG:4326",
                   "--huella", huella, "--clima", str(CLIMA), "--campana", "2024",
                   "--salida", str(tmp_path / destino), *extra])  # fmt: skip
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    resumen = json.loads((tmp_path / destino / "resumen.json").read_text(encoding="utf-8"))
    return resumen, salida


def test_rf10_con_otra_lista_de_etiquetas_el_recuento_cambia_y_el_aviso_desaparece(tmp_path, capsys):
    huella = _huella_del_mapa(tmp_path, capsys)

    por_defecto, pantalla = _analizar(tmp_path, capsys, huella, "a")
    assert por_defecto["estado_frio"]["dias_estimados"] == 26
    assert por_defecto["parametros"]["clima"]["origenes_estimados"] == ["interpolado"]
    assert "Advertencia DIAS_ESTIMADOS" in pantalla

    otra, pantalla = _analizar(tmp_path, capsys, huella, "b", "--origenes-estimados", "satelital, otra")
    assert otra["estado_frio"]["dias_estimados"] == 0
    assert otra["parametros"]["clima"]["origenes_estimados"] == ["satelital", "otra"]
    assert "DIAS_ESTIMADOS" not in pantalla

    con_las_dos, _ = _analizar(tmp_path, capsys, huella, "c", "--origenes-estimados", "INTA_verificado,interpolado")
    assert con_las_dos["estado_frio"]["dias_estimados"] == 123  # todas las etiquetas del invierno 2024


def test_rf8_cambiar_la_lista_no_cambia_el_estado_ni_las_horas(tmp_path, capsys):
    huella = _huella_del_mapa(tmp_path, capsys)
    uno, _ = _analizar(tmp_path, capsys, huella, "a")
    otro, _ = _analizar(tmp_path, capsys, huella, "b", "--origenes-estimados", "satelital")
    for clave in ("estado", "periodo", "horas", "cobertura", "hueco_maximo"):
        assert uno["estado_frio"][clave] == otro["estado_frio"][clave]
    assert uno["resumen"] == otro["resumen"]
