"""T4.8: subcomando `kvpi`, su pantalla y sus códigos de salida (RF-17 y RF-18 de la spec 004)."""

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking import cli
from kiwitracking.cli import main

SERIE = (
    "id,campaña,KVPI\n"
    "4,2019_2020,0.2\n4,2020_2021,0.4\n4,2021_2022,0.6\n"
    "26,2019_2020,0.3\n26,2020_2021,0.5\n"
    "31,2019_2020,0.7\n"
)
MUESTREO = "id,X,Y,row_index\n4,10.5,-20.5,1\n26,11.5,-21.5,2\n31,12.5,-22.5,3\n99,13.5,-23.5,4\n"


@pytest.fixture
def entradas(tmp_path):
    serie, muestreo = tmp_path / "serie.csv", tmp_path / "muestreo.csv"
    serie.write_text(SERIE, encoding="utf-8")
    muestreo.write_text(MUESTREO, encoding="utf-8")
    return str(serie), str(muestreo)


def _kvpi(entradas, *extra):
    return ["kvpi", "--serie", entradas[0], "--muestreo", entradas[1], *extra]


def _correr(argv, capsys):
    codigo = main(argv)
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def test_rf18_la_ayuda_general_lista_el_comando_kvpi(capsys):
    codigo, salida, error = _correr(["--help"], capsys)
    assert codigo == 0
    assert "kvpi" in salida + error


def test_rf18_la_ayuda_de_kvpi_describe_sus_opciones_en_espanol(capsys):
    codigo, salida, _ = _correr(["kvpi", "--help"], capsys)
    assert codigo == 0
    assert salida.startswith("uso:")
    for opcion in (
        "--serie", "--muestreo", "--salida", "--min-campanas", "--campanas",
        "--cobertura-minima-campana", "--sobrescribir", "--depurar",
    ):  # fmt: skip
        assert opcion in salida


@pytest.mark.parametrize("faltante", ["--serie", "--muestreo"])
def test_rf18_sin_una_opcion_obligatoria_el_codigo_es_2(entradas, capsys, faltante):
    argv = _kvpi(entradas)
    posicion = argv.index(faltante)
    del argv[posicion : posicion + 2]
    codigo, _, error = _correr(argv, capsys)
    assert codigo == 2
    assert faltante in error


def test_rf18_kvpi_no_acepta_las_opciones_de_mapa_y_analizar(entradas, capsys):
    codigo, _, _ = _correr(_kvpi(entradas, "--plantas", "x.csv"), capsys)
    assert codigo == 2


def test_rf17_termina_con_codigo_0_y_escribe_el_archivo_por_defecto(entradas, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    codigo, _, error = _correr(_kvpi(entradas), capsys)
    assert codigo == 0 and error == ""
    tabla = pd.read_csv(tmp_path / "plantas_kvpi.csv", dtype={"id": str})
    assert list(tabla.columns) == ["id", "KVPI_mean", "KVPI_std", "KVPI_cv", "n_campanas", "X", "Y", "row_index"]
    assert list(tabla["id"]) == ["4", "26", "31"]


def test_rf17_la_salida_se_puede_elegir(entradas, tmp_path, capsys):
    destino = tmp_path / "otra" / "resultado.csv"
    codigo, salida, _ = _correr(_kvpi(entradas, "--salida", str(destino)), capsys)
    assert codigo == 0
    assert destino.is_file()
    assert str(destino) in salida


def test_rf17_la_pantalla_muestra_la_cantidad_de_plantas_del_resultado(entradas, tmp_path, capsys):
    _, salida, _ = _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert "Plantas en el resultado: 3" in salida


def test_rf17_la_pantalla_muestra_las_campanas_encontradas_con_su_cobertura(entradas, tmp_path, capsys):
    _, salida, _ = _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert "2019_2020: 3 plantas con dato (75,0 %)" in salida  # 3 de las 4 plantas del muestreo
    assert "2020_2021: 2 plantas con dato (50,0 %)" in salida
    assert "2021_2022: 1 planta con dato (25,0 %)" in salida
    assert "4 plantas del muestreo" in salida


def test_rf17_la_pantalla_muestra_cuantas_plantas_tienen_cada_cantidad_de_campanas(entradas, tmp_path, capsys):
    _, salida, _ = _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert "Plantas según las campañas con dato:" in salida
    assert "3 campañas: 1 planta" in salida
    assert "2 campañas: 1 planta" in salida
    assert "1 campaña: 1 planta" in salida


def test_rf17_la_pantalla_muestra_las_advertencias(entradas, tmp_path, capsys):
    _, salida, _ = _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert "Advertencia PLANTAS_CON_MENOS_CAMPANAS:" in salida
    assert "Advertencia SIN_DESVIO:" in salida
    assert "Advertencia PLANTAS_SIN_SERIE:" in salida
    assert "Advertencia CAMPANA_CON_POCOS_DATOS:" in salida


def test_rf17_la_pantalla_dice_donde_quedo_el_archivo_y_como_usarlo(entradas, tmp_path, capsys):
    destino = tmp_path / "r.csv"
    _, salida, _ = _correr(_kvpi(entradas, "--salida", str(destino)), capsys)
    assert f"Resultado guardado en {destino}" in salida
    ultima = salida.strip().splitlines()[-1]
    assert "--plantas" in ultima and "mapa" in ultima and "analizar" in ultima


def test_rf17_el_resumen_va_antes_que_las_advertencias_y_el_archivo_al_final(entradas, tmp_path, capsys):
    _, salida, _ = _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert salida.index("Plantas en el resultado") < salida.index("Campañas") < salida.index("Advertencia")
    assert salida.index("Advertencia") < salida.index("Resultado guardado")


def test_rf17_sin_advertencias_no_imprime_ninguna(tmp_path, capsys):
    serie, muestreo = tmp_path / "s.csv", tmp_path / "m.csv"
    serie.write_text("id,campaña,KVPI\n1,a,0.1\n1,b,0.2\n2,a,0.3\n2,b,0.4\n", encoding="utf-8")
    muestreo.write_text("id,X,Y\n1,1.0,1.0\n2,2.0,2.0\n", encoding="utf-8")
    codigo, salida, _ = _correr(_kvpi((str(serie), str(muestreo)), "--salida", str(tmp_path / "r.csv")), capsys)
    assert codigo == 0 and "Advertencia" not in salida


def test_rf16_no_sobrescribe_sin_la_opcion_y_da_codigo_1(entradas, tmp_path, capsys):
    destino = tmp_path / "r.csv"
    destino.write_text("anterior\n", encoding="utf-8")
    codigo, salida, error = _correr(_kvpi(entradas, "--salida", str(destino)), capsys)
    assert codigo == 1
    assert error.startswith("Error:") and "--sobrescribir" in error
    assert salida == ""
    assert destino.read_text(encoding="utf-8") == "anterior\n"


def test_rf16_con_sobrescribir_reemplaza_el_archivo(entradas, tmp_path, capsys):
    destino = tmp_path / "r.csv"
    destino.write_text("anterior\n", encoding="utf-8")
    codigo, _, _ = _correr(_kvpi(entradas, "--salida", str(destino), "--sobrescribir"), capsys)
    assert codigo == 0
    assert destino.read_text(encoding="utf-8").startswith("id,KVPI_mean")


def test_rf18_un_error_de_entrada_da_codigo_1_y_mensaje_sin_traza(tmp_path, capsys):
    serie, muestreo = tmp_path / "s.csv", tmp_path / "m.csv"
    serie.write_text("id,campaña,KVPI\n1,a,n/d\n", encoding="utf-8")
    muestreo.write_text("id,X,Y\n1,1.0,1.0\n", encoding="utf-8")
    destino = tmp_path / "r.csv"
    codigo, salida, error = _correr(_kvpi((str(serie), str(muestreo)), "--salida", str(destino)), capsys)
    assert codigo == 1
    assert error.startswith("Error:") and "n/d" in error
    assert "Traceback" not in error and salida == ""
    assert not destino.exists()


def test_rf18_un_archivo_inexistente_da_codigo_1_y_lo_nombra(tmp_path, capsys):
    muestreo = tmp_path / "m.csv"
    muestreo.write_text("id,X,Y\n1,1.0,1.0\n", encoding="utf-8")
    codigo, _, error = _correr(["kvpi", "--serie", str(tmp_path / "no_esta.csv"), "--muestreo", str(muestreo)], capsys)
    assert codigo == 1 and "no_esta.csv" in error


def test_rf19_un_error_no_deja_archivos_de_salida(tmp_path, capsys):
    serie, muestreo = tmp_path / "s.csv", tmp_path / "m.csv"
    serie.write_text("id,campaña,KVPI\n1,a,0.1\n", encoding="utf-8")
    muestreo.write_text("id,X,Y\n9,1.0,1.0\n", encoding="utf-8")  # ninguna planta en común
    codigo, _, _ = _correr(_kvpi((str(serie), str(muestreo)), "--salida", str(tmp_path / "sub" / "r.csv")), capsys)
    assert codigo == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["m.csv", "s.csv"]


def test_rf19_no_modifica_los_archivos_de_entrada(entradas, tmp_path, capsys):
    antes = [Path(ruta).read_bytes() for ruta in entradas]
    _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert [Path(ruta).read_bytes() for ruta in entradas] == antes


def test_rf18_un_error_inesperado_da_codigo_3_y_muestra_la_traza_solo_con_depurar(entradas, tmp_path, monkeypatch, capsys):
    def fallar(*_a, **_k):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(cli, "ejecutar_kvpi", fallar)
    argv = _kvpi(entradas, "--salida", str(tmp_path / "r.csv"))
    codigo, _, error = _correr(argv, capsys)
    assert codigo == 3
    assert "Error inesperado: RuntimeError: falla simulada" in error and "Traceback" not in error
    codigo, _, error = _correr(argv + ["--depurar"], capsys)
    assert codigo == 3 and "Traceback" in error


def test_rf18_sin_indicar_los_parametros_se_usan_los_del_flujo(entradas, tmp_path, monkeypatch, capsys):
    recibidos = {}
    real = cli.ejecutar_kvpi

    def espiar(*argumentos, **nombrados):
        recibidos.update(nombrados)
        return real(*argumentos, **nombrados)

    monkeypatch.setattr(cli, "ejecutar_kvpi", espiar)
    _correr(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), capsys)
    assert recibidos == {}


def test_rf18_los_parametros_indicados_llegan_al_flujo(entradas, tmp_path, monkeypatch, capsys):
    recibidos = {}
    real = cli.ejecutar_kvpi

    def espiar(*argumentos, **nombrados):
        recibidos.update(nombrados)
        return real(*argumentos, **nombrados)

    monkeypatch.setattr(cli, "ejecutar_kvpi", espiar)
    argv = _kvpi(
        entradas, "--salida", str(tmp_path / "r.csv"), "--min-campanas", "3",
        "--campanas", "2019_2020, 2020_2021,2021_2022", "--cobertura-minima-campana", "0.1",
    )  # fmt: skip
    codigo, _, _ = _correr(argv, capsys)
    assert codigo == 0
    assert recibidos == {
        "min_campanas": 3,
        "campanas": ["2019_2020", "2020_2021", "2021_2022"],
        "cobertura_minima_campana": 0.1,
    }


def test_rf18_min_campanas_3_deja_sin_desvio_a_quienes_no_llegan(entradas, tmp_path, capsys):
    destino = tmp_path / "r.csv"
    codigo, salida, _ = _correr(_kvpi(entradas, "--salida", str(destino), "--min-campanas", "3"), capsys)
    assert codigo == 0
    tabla = pd.read_csv(destino)
    assert tabla["KVPI_std"].notna().sum() == 1  # solo la planta 4 tiene 3 campañas


def test_rf18_min_campanas_no_permitido_da_codigo_1(entradas, capsys):
    codigo, _, error = _correr(_kvpi(entradas, "--min-campanas", "1"), capsys)
    assert codigo == 1 and "min_campanas" in error


def test_rf18_min_campanas_que_no_es_numero_da_codigo_2(entradas, capsys):
    codigo, _, _ = _correr(_kvpi(entradas, "--min-campanas", "abc"), capsys)
    assert codigo == 2


def test_rf18_cobertura_minima_fuera_de_rango_da_codigo_1_y_texto_da_2(entradas, capsys):
    assert _correr(_kvpi(entradas, "--cobertura-minima-campana", "1.5"), capsys)[0] == 1
    assert _correr(_kvpi(entradas, "--cobertura-minima-campana", "abc"), capsys)[0] == 2


def test_rf18_campanas_esperadas_que_no_coinciden_dan_codigo_1_y_las_nombran(entradas, capsys):
    codigo, _, error = _correr(_kvpi(entradas, "--campanas", "2019_2020,2020_2021,2024_2025"), capsys)
    assert codigo == 1 and "2024_2025" in error and "2021_2022" in error


def test_rf18_campanas_vacias_dan_codigo_1(entradas, capsys):
    codigo, _, error = _correr(_kvpi(entradas, "--campanas", ""), capsys)
    assert codigo == 1 and "Error:" in error


def test_rf15_rutas_con_espacios_y_tildes(tmp_path, capsys):
    carpeta = tmp_path / "carpeta con ñandú"
    carpeta.mkdir()
    serie, muestreo = carpeta / "serie ñ.csv", carpeta / "muestreo ñ.csv"
    serie.write_text(SERIE, encoding="utf-8")
    muestreo.write_text(MUESTREO, encoding="utf-8")
    destino = carpeta / "resultado ñ.csv"
    codigo, _, _ = _correr(_kvpi((str(serie), str(muestreo)), "--salida", str(destino)), capsys)
    assert codigo == 0 and destino.is_file()


def _proceso(args, cwd, **entorno):
    variables = {**os.environ, "PYTHONIOENCODING": "utf-8", **entorno}
    return subprocess.run(
        [sys.executable, "-m", "kiwitracking", *args], cwd=cwd, env=variables, capture_output=True, text=True, encoding="utf-8"
    )


def test_rf18_en_un_proceso_aparte_el_codigo_de_salida_es_el_real(entradas, tmp_path):
    ok = _proceso(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), tmp_path)
    assert ok.returncode == 0 and "Resultado guardado" in ok.stdout
    repetido = _proceso(_kvpi(entradas, "--salida", str(tmp_path / "r.csv")), tmp_path)
    assert repetido.returncode == 1
    assert repetido.stderr.startswith("Error:") and "Traceback" not in repetido.stderr
    uso = _proceso(["kvpi"], tmp_path)
    assert uso.returncode == 2


def test_rf18_con_la_consola_en_ascii_la_pantalla_no_falla(entradas, tmp_path):
    proceso = subprocess.run(
        [sys.executable, "-m", "kiwitracking", *_kvpi(entradas, "--salida", str(tmp_path / "r.csv"))],
        cwd=tmp_path, env={**os.environ, "PYTHONIOENCODING": "ascii"}, capture_output=True,
    )  # fmt: skip
    assert proceso.returncode == 0, proceso.stderr
