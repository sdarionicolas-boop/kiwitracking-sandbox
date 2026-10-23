"""Línea de comandos `kiwitracking` (spec 003, RF-1 en esta tarea; el resto se agrega tarea por tarea)."""

import dataclasses
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.cli import construir_parser, interpretar_analizar, main
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada

RAIZ = Path(__file__).parent.parent


# --- T3.0: programa y ayuda (RF-1) --------------------------------------------------------------


def _nombra(texto, opcion):
    """La opción aparece completa (no como prefijo de otra más larga)."""
    return re.search(re.escape(opcion) + r"(?![\w-])", texto) is not None


def test_rf1_main_devuelve_el_codigo_como_entero_y_no_termina_el_proceso(capsys):
    codigo = main(["--help"])  # si llamara a sys.exit, el test se cortaría con SystemExit

    assert codigo == 0 and isinstance(codigo, int)


def test_rf1_con_help_muestra_una_ayuda_en_espanol_con_los_dos_subcomandos(capsys):
    main(["--help"])

    salida = capsys.readouterr().out
    assert "uso:" in salida and "usage:" not in salida
    assert "kiwitracking" in salida and "mapa" in salida and "analizar" in salida


def test_rf1_sin_subcomando_muestra_la_ayuda_por_la_salida_de_errores_y_da_codigo_2(capsys):
    codigo = main([])

    captura = capsys.readouterr()
    assert codigo == 2
    assert "mapa" in captura.err and "analizar" in captura.err
    assert captura.out == ""


def test_rf1_un_subcomando_desconocido_da_error_de_uso_con_codigo_2(capsys):
    codigo = main(["inventado"])

    assert codigo == 2
    assert "inventado" in capsys.readouterr().err


def test_rf1_la_ayuda_de_mapa_nombra_sus_opciones(capsys):
    codigo = main(["mapa", "--help"])

    salida = capsys.readouterr().out
    assert codigo == 0
    for opcion in ("--plantas", "--malla", "--crs-plantas", "--salida", "--sin-fondo-satelital", "--sobrescribir", "--depurar"):
        assert _nombra(salida, opcion), opcion


def test_rf1_la_ayuda_de_analizar_nombra_sus_opciones(capsys):
    codigo = main(["analizar", "--help"])

    salida = capsys.readouterr().out
    assert codigo == 0
    opciones = (
        "--plantas", "--malla", "--crs-plantas", "--depurar", "--huella", "--salida", "--sobrescribir",
        "--correccion", "--prueba-t", "--alfa", "--min-plantas-grupo", "--p-ambiente", "--p-estabilidad",
        "--no-escalar-std", "--clima", "--campana", "--ventana-frio", "--formato-fecha", "--cobertura-minima",
        "--max-hueco-dias", "--estado-frio",
    )
    for opcion in opciones:
        assert _nombra(salida, opcion), opcion


def test_rf1_una_opcion_desconocida_da_error_de_uso_con_codigo_2(capsys):
    codigo = main(["mapa", "--plantas", "x.csv", "--no-existe"])

    assert codigo == 2
    assert "--no-existe" in capsys.readouterr().err


def test_rf1_python_m_kiwitracking_muestra_la_ayuda_en_un_proceso_aparte():
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # la codificación de la consola es tema de T3.9 (RF-22)
    proceso = subprocess.run(
        [sys.executable, "-m", "kiwitracking", "--help"], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ, env=entorno
    )

    assert proceso.returncode == 0
    assert "mapa" in proceso.stdout and "analizar" in proceso.stdout


def test_rf1_pyproject_declara_el_punto_de_entrada_kiwitracking():
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")

    assert "[project.scripts]" in texto
    assert 'kiwitracking = "kiwitracking.cli:main"' in texto


def test_rf1_los_errores_de_uso_muestran_el_encabezado_en_espanol(capsys):
    main(["inventado"])

    assert capsys.readouterr().err.startswith("uso: ")


def test_rf1_python_m_kiwitracking_propaga_el_codigo_de_salida_de_un_error_de_uso():
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run(
        [sys.executable, "-m", "kiwitracking", "inventado"], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ, env=entorno
    )

    assert proceso.returncode == 2


# --- T3.3: comando mapa (RF-6, RF-7, RF-26) ------------------------------------------------------

GOLDEN = RAIZ / "tests" / "golden"


def _argumentos_de_mapa(tmp_path, *extra):
    return [
        "mapa", "--plantas", str(GOLDEN / "datos_plantas_completos.csv"), "--malla", str(GOLDEN / "malla_zona.geojson"),
        "--crs-plantas", "EPSG:4326", "--salida", str(tmp_path / "mapa.html"), "--sin-fondo-satelital", *extra,
    ]


def test_rf6_mapa_imprime_la_cantidad_de_plantas_bajo_malla_y_fuera_de_malla(tmp_path, capsys):
    codigo = main(_argumentos_de_mapa(tmp_path))

    salida = capsys.readouterr().out
    assert codigo == 0
    assert re.search(r"bajo malla: 53\b", salida) and re.search(r"fuera de malla: 106\b", salida)
    assert (tmp_path / "mapa.html").is_file() and str(tmp_path / "mapa.html") in salida


def test_rf26_la_huella_sale_en_una_linea_propia_con_el_formato_exacto(tmp_path, capsys):
    main(_argumentos_de_mapa(tmp_path))

    lineas = capsys.readouterr().out.splitlines()
    huellas = [linea for linea in lineas if linea.startswith("Huella:")]
    assert len(huellas) == 1 and re.fullmatch(r"Huella: [0-9a-f]{12}", huellas[0])


def test_rf6_la_huella_que_imprime_mapa_es_la_del_lote_de_referencia(tmp_path, capsys):
    main(_argumentos_de_mapa(tmp_path))

    lote = pd.read_csv(GOLDEN / "datos_plantas_completos.csv", encoding="utf-8")
    assert f"Huella: {huella(lote)}" in capsys.readouterr().out


def test_rf6_mapa_imprime_las_advertencias(tmp_path, capsys):
    lejos = tmp_path / "lejos.geojson"
    lejos.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":'
        '{"type":"Polygon","coordinates":[[[10,10],[10.1,10],[10.1,10.1],[10,10.1],[10,10]]]}}]}',
        encoding="utf-8",
    )
    argumentos = _argumentos_de_mapa(tmp_path)
    argumentos[argumentos.index("--malla") + 1] = str(lejos)

    main(argumentos)

    assert "POSIBLE_ERROR_COORDENADAS" in capsys.readouterr().out


def test_rf6_sin_salida_el_mapa_se_guarda_como_mapa_html_en_el_directorio_actual(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    argumentos = _argumentos_de_mapa(tmp_path)
    del argumentos[argumentos.index("--salida"): argumentos.index("--salida") + 2]

    main(argumentos)

    assert (tmp_path / "mapa.html").is_file()


def test_rf7_el_mapa_con_sin_fondo_satelital_no_pide_teselas(tmp_path, capsys):
    main(_argumentos_de_mapa(tmp_path))

    assert "arcgisonline" not in (tmp_path / "mapa.html").read_text(encoding="utf-8")


def test_rf6_mapa_sin_sobrescribir_sobre_un_archivo_existente_no_lo_toca(tmp_path, capsys):
    existente = tmp_path / "mapa.html"
    existente.write_text("anterior", encoding="utf-8")

    with pytest.raises(ErrorDeEntrada):  # hasta T3.9 (RF-19) el error sale como excepción, no como código
        main(_argumentos_de_mapa(tmp_path))

    assert existente.read_text(encoding="utf-8") == "anterior"


def test_rf6_mapa_con_sobrescribir_reemplaza_el_archivo_existente(tmp_path, capsys):
    existente = tmp_path / "mapa.html"
    existente.write_text("anterior", encoding="utf-8")

    codigo = main(_argumentos_de_mapa(tmp_path, "--sobrescribir"))

    assert codigo == 0 and "anterior" not in existente.read_text(encoding="utf-8")


# --- T3.4: argumentos de analizar (RF-8, RF-9, RF-11, RF-24) ---------------------------------------------


def _solicitud(*extra, huella_indicada="c4e55ae105c6"):
    argv = ["analizar", "--plantas", "plantas.csv"]
    if huella_indicada is not None:
        argv += ["--huella", huella_indicada]
    return interpretar_analizar(construir_parser().parse_args([*argv, *extra]))


def test_rf8_sin_huella_da_un_error_que_explica_que_hay_que_correr_mapa_primero():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud(huella_indicada=None)

    mensaje = str(error.value)
    assert "--huella" in mensaje and "mapa" in mensaje


@pytest.mark.parametrize("vacia", ["", "   "])
def test_rf8_una_huella_vacia_cuenta_como_ausente(vacia):
    with pytest.raises(ErrorDeEntrada, match="--huella"):
        _solicitud(huella_indicada=vacia)


def test_rf8_la_huella_indicada_llega_a_la_solicitud_sin_cambios():
    assert _solicitud(huella_indicada="abc123def456").huella == "abc123def456"


def test_rf8_la_huella_que_falta_se_detecta_antes_que_los_otros_errores_de_argumentos():
    with pytest.raises(ErrorDeEntrada, match="--huella"):
        _solicitud("--clima", "c.csv", "--estado-frio", "Óptimo", huella_indicada=None)


def test_rf11_clima_y_estado_frio_a_la_vez_son_excluyentes():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--clima", "clima.csv", "--estado-frio", "Óptimo")

    assert "excluyentes" in str(error.value) and "--clima" in str(error.value) and "--estado-frio" in str(error.value)


@pytest.mark.parametrize(
    "escrito, exacto",
    [("optimo", "Óptimo"), ("ÓPTIMO", "Óptimo"), ("Óptimo", "Óptimo"), ("Optimo", "Óptimo"), ("adecuado", "Adecuado"), ("ADECUADO", "Adecuado"), ("deficiente", "Deficiente"), ("  Deficiente ", "Deficiente")],
)
def test_rf11_estado_frio_acepta_el_texto_sin_distinguir_mayusculas_ni_tildes_y_lo_deja_exacto(escrito, exacto):
    assert _solicitud("--estado-frio", escrito).estado_frio == exacto


def test_rf11_un_estado_que_no_coincide_da_el_error_de_valores_permitidos_de_la_spec_001():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--estado-frio", "regular")

    assert "Deficiente, Adecuado, Óptimo" in str(error.value)


def test_rf11_sin_estado_frio_ni_clima_la_solicitud_no_trae_estado():
    solicitud = _solicitud()

    assert solicitud.estado_frio is None and solicitud.clima is None


OPCIONES_DE_CLIMA = [
    ("--campana", "2024"),
    ("--ventana-frio", "temporada"),
    ("--formato-fecha", "%d/%m/%Y"),
    ("--cobertura-minima", "0.8"),
    ("--max-hueco-dias", "10"),
]


@pytest.mark.parametrize("opcion, valor", OPCIONES_DE_CLIMA)
def test_rf24_una_opcion_de_clima_sin_clima_da_un_error_que_la_nombra(opcion, valor):
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud(opcion, valor)

    assert opcion in str(error.value) and "--clima" in str(error.value)


@pytest.mark.parametrize("opcion, valor", OPCIONES_DE_CLIMA)
def test_rf24_tampoco_vale_junto_con_estado_frio(opcion, valor):
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud(opcion, valor, "--estado-frio", "Adecuado")

    assert opcion in str(error.value) and "--clima" in str(error.value)


def test_rf24_si_hay_varias_opciones_de_clima_sin_clima_el_error_las_nombra_todas():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--campana", "2024", "--formato-fecha", "%d/%m/%Y")

    assert "--campana" in str(error.value) and "--formato-fecha" in str(error.value)


@pytest.mark.parametrize("opcion, valor", OPCIONES_DE_CLIMA)
def test_rf24_con_clima_las_opciones_de_clima_se_aceptan(opcion, valor):
    solicitud = _solicitud("--clima", "clima.csv", opcion, valor)

    assert solicitud.clima == "clima.csv"


def test_rf9_sin_opciones_no_se_pasa_nada_y_los_valores_por_defecto_son_los_de_las_funciones():
    solicitud = _solicitud()

    assert solicitud.parametros_analisis == {} and solicitud.parametros_clima == {} and solicitud.campana is None


def test_rf9_cada_parametro_de_la_spec_001_llega_con_el_nombre_de_analizar():
    solicitud = _solicitud(
        "--correccion", "forzar", "--prueba-t", "student", "--alfa", "0.01", "--min-plantas-grupo", "3",
        "--p-ambiente", "30", "60", "--p-estabilidad", "80", "--no-escalar-std",
    )

    assert solicitud.parametros_analisis == {
        "correccion": "forzar", "prueba_t": "student", "alfa": 0.01, "min_plantas_grupo": 3,
        "p_ambiente": (30.0, 60.0), "p_estabilidad": 80.0, "escalar_std": False,
    }
    assert set(solicitud.parametros_analisis) <= set(inspect.signature(analizar).parameters)


def test_rf9_cada_parametro_de_clima_llega_con_el_nombre_de_parametros_clima():
    solicitud = _solicitud(
        "--clima", "clima.csv", "--campana", "2024", "--ventana-frio", "temporada", "--formato-fecha", "%d/%m/%Y",
        "--cobertura-minima", "0.8", "--max-hueco-dias", "10",
    )

    assert solicitud.parametros_clima == {"ventana_frio": "temporada", "formato_fecha": "%d/%m/%Y", "cobertura_minima": 0.8, "max_hueco_dias": 10}
    assert solicitud.campana == 2024
    assert set(solicitud.parametros_clima) <= {campo.name for campo in dataclasses.fields(ParametrosClima)}


def test_rf9_max_hueco_dias_ninguno_pasa_none():
    solicitud = _solicitud("--clima", "clima.csv", "--max-hueco-dias", "ninguno")

    assert solicitud.parametros_clima == {"max_hueco_dias": None}


def test_rf9_max_hueco_dias_que_no_es_un_numero_ni_ninguno_da_un_error_que_nombra_la_opcion():
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--clima", "clima.csv", "--max-hueco-dias", "muchos")

    assert "--max-hueco-dias" in str(error.value) and "ninguno" in str(error.value)


@pytest.mark.parametrize("opcion, valor, permitidos", [("--correccion", "inventado", "auto, forzar, desactivar"), ("--prueba-t", "z", "welch, student")])
def test_rf9_un_valor_no_permitido_de_la_spec_001_da_el_error_que_nombra_los_permitidos(opcion, valor, permitidos):
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud(opcion, valor)

    assert permitidos in str(error.value)


@pytest.mark.parametrize("opcion, valor, permitido", [("--ventana-frio", "verano", "invierno"), ("--cobertura-minima", "2", "entre 0 y 1")])
def test_rf9_un_valor_no_permitido_de_clima_da_el_error_de_la_spec_002_antes_de_leer_archivos(opcion, valor, permitido):
    with pytest.raises(ErrorDeEntrada) as error:
        _solicitud("--clima", "no_existe.csv", opcion, valor)  # el archivo no existe: el error es el del valor

    assert permitido in str(error.value)
