"""El script que prueba la instalación en un entorno limpio (spec 006, RF-14).

El script de verdad tarda más de un minuto y necesita internet, así que se corre aparte (y su resultado queda en
`validacion.md`). Estos tests, sin red, comprueban que existe, que lee bien el README y que maneja sus errores.
"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "probar_instalacion.py"


@pytest.fixture
def modulo():
    especificacion = importlib.util.spec_from_file_location("probar_instalacion", SCRIPT)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def test_rf14_el_script_existe_y_esta_documentado_en_la_guia():
    assert SCRIPT.is_file()
    guia = (RAIZ / "docs" / "uso.md").read_text(encoding="utf-8")
    assert "python scripts/probar_instalacion.py" in guia


def test_rf14_la_ayuda_del_script_funciona_en_un_proceso_aparte():
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, env=entorno, cwd=RAIZ)
    assert proceso.returncode == 0
    for texto in ("--wheel", "--conservar", "entorno"):
        assert texto in proceso.stdout


def test_rf14_el_script_hace_lo_que_la_guia_dice():
    fuente = SCRIPT.read_text(encoding="utf-8")
    for comando in ('"--version"', '"--help"', '"-m", "kiwitracking"', "venv", "pip", "build"):
        assert comando in fuente, f"el script no hace: {comando}"


def test_rf14_lee_el_ejemplo_minimo_del_readme(modulo):
    comandos = modulo.leer_ejemplo((RAIZ / "README.md").read_text(encoding="utf-8"))
    assert [c.split()[1] for c in comandos] == ["kvpi", "mapa", "analizar"]
    assert all(c.startswith("kiwitracking ") for c in comandos)


def test_rf14_sin_el_bloque_marcado_el_error_dice_que_falta(modulo):
    with pytest.raises(modulo.FalloDeInstalacion, match="ejemplo mínimo"):
        modulo.leer_ejemplo("# Sin ejemplo\n")


def test_rf14_la_version_esperada_sale_de_pyproject(modulo):
    assert re.fullmatch(r"\d+\.\d+\.\d+", modulo.version_del_proyecto())


def test_rf14_comprobar_la_salida_de_version(modulo):
    modulo.comprobar_version("kiwitracking 1.2.0\n", "1.2.0")
    with pytest.raises(modulo.FalloDeInstalacion, match="1.1.0"):
        modulo.comprobar_version("kiwitracking 1.1.0\n", "1.2.0")
    with pytest.raises(modulo.FalloDeInstalacion):
        modulo.comprobar_version("kiwitracking desconocida\n", "1.2.0")


def test_rf14_el_entorno_de_los_procesos_hijos_no_hereda_la_variable_que_desactiva_el_bytecode(modulo, monkeypatch):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    entorno = modulo.entorno_de_los_hijos()
    assert "PYTHONDONTWRITEBYTECODE" not in entorno and entorno["PYTHONIOENCODING"] == "utf-8"


def test_rf14_un_wheel_que_no_existe_da_codigo_1_y_lo_nombra_sin_crear_nada(modulo, tmp_path, capsys, monkeypatch):
    def no_deberia_llamarse(*_a, **_k):
        raise AssertionError("no se debe crear el entorno si el wheel no existe")

    monkeypatch.setattr(modulo, "crear_entorno", no_deberia_llamarse)
    codigo = modulo.main(["--wheel", str(tmp_path / "no_esta-1.2.0-py3-none-any.whl")])
    salida = capsys.readouterr()
    assert codigo == 1
    assert "no_esta-1.2.0-py3-none-any.whl" in salida.out + salida.err


def test_rf14_un_archivo_que_no_es_un_wheel_da_codigo_1(modulo, tmp_path, capsys):
    otro = tmp_path / "otro.txt"
    otro.write_text("x", encoding="utf-8")
    assert modulo.main(["--wheel", str(otro)]) == 1
    assert ".whl" in capsys.readouterr().out


def test_rf14_un_paso_que_falla_da_codigo_1_y_dice_cual(modulo, tmp_path, capsys, monkeypatch):
    def falla(*_a, **_k):
        raise modulo.FalloDeInstalacion("pip no pudo instalar el paquete")

    wheel = tmp_path / "kiwitracking-1.2.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    monkeypatch.setattr(modulo, "crear_entorno", lambda carpeta: tmp_path / "python")
    monkeypatch.setattr(modulo, "instalar", falla)
    assert modulo.main(["--wheel", str(wheel)]) == 1
    salida = capsys.readouterr().out
    assert "ERROR" in salida and "pip no pudo instalar el paquete" in salida


def test_rf14_si_todos_los_pasos_andan_da_codigo_0_y_dice_que_la_instalacion_esta_verificada(modulo, tmp_path, capsys, monkeypatch):
    wheel = tmp_path / "kiwitracking-1.2.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    monkeypatch.setattr(modulo, "crear_entorno", lambda carpeta: tmp_path / "python")
    monkeypatch.setattr(modulo, "instalar", lambda python, wheel: None)
    monkeypatch.setattr(modulo, "comprobar_instalacion", lambda python, carpeta_de_trabajo: None)
    assert modulo.main(["--wheel", str(wheel)]) == 0
    assert "verificada" in capsys.readouterr().out


def test_rf14_el_script_borra_su_carpeta_temporal_salvo_con_conservar(modulo, tmp_path, monkeypatch, capsys):
    wheel = tmp_path / "kiwitracking-1.2.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    creadas = []
    monkeypatch.setattr(modulo, "crear_entorno", lambda carpeta: creadas.append(carpeta) or tmp_path / "python")
    monkeypatch.setattr(modulo, "instalar", lambda python, wheel: None)
    monkeypatch.setattr(modulo, "comprobar_instalacion", lambda python, carpeta_de_trabajo: None)
    assert modulo.main(["--wheel", str(wheel)]) == 0
    assert not creadas[0].parent.exists()  # borrada
    assert modulo.main(["--wheel", str(wheel), "--conservar"]) == 0
    assert creadas[1].parent.exists()  # conservada
    import shutil

    shutil.rmtree(creadas[1].parent, ignore_errors=True)
