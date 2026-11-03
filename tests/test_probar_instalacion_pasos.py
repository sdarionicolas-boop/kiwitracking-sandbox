"""Los pasos internos del script de instalación, sin red ni entorno nuevo (spec 006, RF-14).

`ejecutar` se reemplaza por una función que devuelve lo que imprimiría cada comando, para comprobar qué verifica el script.
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "probar_instalacion.py"
VERSION = "1.2.0"


@pytest.fixture
def modulo():
    especificacion = importlib.util.spec_from_file_location("probar_instalacion_pasos", SCRIPT)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


# --- ejecutar -----------------------------------------------------------------------------------------------------


def test_rf14_ejecutar_devuelve_lo_que_el_comando_imprime(modulo, capsys):
    salida = modulo.ejecutar([sys.executable, "-c", "print('hola')"], None, "decir hola")
    assert salida == "hola\n"
    assert "decir hola" in capsys.readouterr().out


def test_rf14_ejecutar_falla_con_el_codigo_y_lo_que_imprimio_si_el_comando_no_termina_bien(modulo):
    with pytest.raises(modulo.FalloDeInstalacion, match="código 3") as error:
        modulo.ejecutar([sys.executable, "-c", "import sys; print('algo salió mal'); sys.exit(3)"], None, "un comando roto")
    assert "un comando roto" in str(error.value) and "algo salió mal" in str(error.value)


def test_rf14_ejecutar_lee_la_salida_en_utf8_aunque_la_consola_use_otra_codificacion(modulo, monkeypatch):
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    salida = modulo.ejecutar([sys.executable, "-c", "print('Óptimo ñandú')"], None, "imprimir tildes")
    assert salida == "Óptimo ñandú\n"


def test_rf14_ejecutar_no_hereda_la_variable_que_desactiva_el_bytecode(modulo, monkeypatch):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    salida = modulo.ejecutar([sys.executable, "-c", "import sys; print(sys.dont_write_bytecode)"], None, "ver el bytecode")
    assert salida.strip() == "False"


# --- construir ----------------------------------------------------------------------------------------------------


def test_rf14_construir_borra_el_egg_info_viejo_antes_de_construir(modulo, tmp_path, monkeypatch):
    (tmp_path / "kiwitracking.egg-info").mkdir()
    (tmp_path / "kiwitracking.egg-info" / "SOURCES.txt").write_text("viejo", encoding="utf-8")
    monkeypatch.setattr(modulo, "RAIZ", tmp_path)
    vistas = []

    def falsa(argumentos, cwd, descripcion):
        vistas.append((tmp_path / "kiwitracking.egg-info").exists())
        salida = Path(argumentos[argumentos.index("--outdir") + 1])
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "kiwitracking-1.2.0-py3-none-any.whl").write_bytes(b"")
        return ""

    monkeypatch.setattr(modulo, "ejecutar", falsa)
    wheel = modulo.construir(tmp_path / "dist")
    assert vistas == [False]  # ya no existía cuando se construyó
    assert wheel.name == "kiwitracking-1.2.0-py3-none-any.whl"


def test_rf14_construir_falla_si_no_sale_exactamente_un_wheel(modulo, tmp_path, monkeypatch):
    monkeypatch.setattr(modulo, "RAIZ", tmp_path)
    monkeypatch.setattr(modulo, "ejecutar", lambda *a, **k: (tmp_path / "dist").mkdir(exist_ok=True) or "")
    with pytest.raises(modulo.FalloDeInstalacion, match="un wheel"):
        modulo.construir(tmp_path / "dist")


# --- archivos de ejemplo ------------------------------------------------------------------------------------------


def test_rf14_los_archivos_de_ejemplo_se_arman_con_los_datos_de_referencia(modulo, tmp_path):
    modulo._preparar_archivos_de_ejemplo(tmp_path / "trabajo")
    muestreo = pd.read_csv(tmp_path / "trabajo" / "muestreo.csv")
    assert list(muestreo.columns) == ["id", "X", "Y"] and len(muestreo) == 159
    for nombre in ("serie.csv", "malla.geojson", "clima_diario.csv"):
        assert (tmp_path / "trabajo" / nombre).is_file()


def test_rf14_sin_los_datos_de_referencia_el_error_dice_que_se_corre_desde_el_repositorio(modulo, tmp_path, monkeypatch):
    monkeypatch.setattr(modulo, "RAIZ", tmp_path)
    with pytest.raises(modulo.FalloDeInstalacion, match="repositorio"):
        modulo._preparar_archivos_de_ejemplo(tmp_path / "trabajo")


# --- comprobar_instalacion ----------------------------------------------------------------------------------------


def _entorno_falso(tmp_path):
    scripts = tmp_path / "entorno" / ("Scripts" if sys.platform == "win32" else "bin")
    scripts.mkdir(parents=True)
    python = scripts / ("python.exe" if sys.platform == "win32" else "python")
    programa = scripts / ("kiwitracking.exe" if sys.platform == "win32" else "kiwitracking")
    python.write_bytes(b"")
    programa.write_bytes(b"")
    return python, programa


def _salidas(tmp_path, huella="c4e55ae105c6", **cambios):
    paquete = tmp_path / "entorno" / "Lib" / "site-packages" / "kiwitracking" / "__init__.py"
    salidas = {
        "version": f"kiwitracking {VERSION}\n",
        "ayuda": "uso: kiwitracking {mapa,analizar,kvpi}\n",
        "donde": f"{paquete}\n",
        "kvpi": "Plantas en el resultado: 159\n",
        "mapa": f"Huella: {huella}\n",
        "analizar": "Plantas analizadas: 159\n",
    }
    salidas.update(cambios)
    return salidas


def _con_ejecucion_falsa(modulo, monkeypatch, salidas):
    llamadas = []

    def falsa(argumentos, cwd, descripcion):
        llamadas.append([str(a) for a in argumentos])
        texto = " ".join(str(a) for a in argumentos)
        if "--version" in texto:
            return salidas["version"]
        if "--help" in texto:
            return salidas["ayuda"]
        if "import kiwitracking" in texto:
            return salidas["donde"]
        return salidas[str(argumentos[1])]

    monkeypatch.setattr(modulo, "ejecutar", falsa)
    return llamadas


def test_rf14_comprobar_instalacion_corre_los_comandos_en_orden_y_pasa_la_huella_del_mapa_al_analisis(modulo, tmp_path, monkeypatch):
    python, programa = _entorno_falso(tmp_path)
    llamadas = _con_ejecucion_falsa(modulo, monkeypatch, _salidas(tmp_path))
    modulo.comprobar_instalacion(python, tmp_path / "trabajo")
    assert [l[1] for l in llamadas if l[0] == str(programa)] == ["--version", "--help", "kvpi", "mapa", "analizar"]
    assert any(l[1:4] == ["-m", "kiwitracking", "--help"] for l in llamadas)
    analizar = next(l for l in llamadas if l[1] == "analizar")
    assert "c4e55ae105c6" in analizar and "HUELLA" not in analizar


def test_rf14_comprobar_instalacion_falla_si_el_comando_no_se_creo(modulo, tmp_path, monkeypatch):
    python, programa = _entorno_falso(tmp_path)
    programa.unlink()
    _con_ejecucion_falsa(modulo, monkeypatch, _salidas(tmp_path))
    with pytest.raises(modulo.FalloDeInstalacion, match="no creó el comando"):
        modulo.comprobar_instalacion(python, tmp_path / "trabajo")


def test_rf14_comprobar_instalacion_falla_si_la_version_no_es_la_del_proyecto(modulo, tmp_path, monkeypatch):
    python, _ = _entorno_falso(tmp_path)
    _con_ejecucion_falsa(modulo, monkeypatch, _salidas(tmp_path, version="kiwitracking 0.0.1\n"))
    with pytest.raises(modulo.FalloDeInstalacion, match="0.0.1"):
        modulo.comprobar_instalacion(python, tmp_path / "trabajo")


def test_rf14_comprobar_instalacion_falla_si_la_ayuda_no_lista_los_comandos(modulo, tmp_path, monkeypatch):
    python, _ = _entorno_falso(tmp_path)
    _con_ejecucion_falsa(modulo, monkeypatch, _salidas(tmp_path, ayuda="otra cosa\n"))
    with pytest.raises(modulo.FalloDeInstalacion, match="kvpi"):
        modulo.comprobar_instalacion(python, tmp_path / "trabajo")


def test_rf14_comprobar_instalacion_falla_si_el_paquete_se_importa_desde_el_repositorio(modulo, tmp_path, monkeypatch):
    python, _ = _entorno_falso(tmp_path)
    salidas = _salidas(tmp_path, donde=str(RAIZ / "kiwitracking" / "__init__.py") + "\n")
    _con_ejecucion_falsa(modulo, monkeypatch, salidas)
    with pytest.raises(modulo.FalloDeInstalacion, match="se importó el paquete desde"):
        modulo.comprobar_instalacion(python, tmp_path / "trabajo")


@pytest.mark.parametrize("comando, cambio", [
    ("kvpi", {"kvpi": "otra cosa\n"}),
    ("mapa", {"mapa": "Huella: 000000000000\n"}),
    ("analizar", {"analizar": "Plantas analizadas: 10\n"}),
])  # fmt: skip
def test_rf14_comprobar_instalacion_falla_si_el_ejemplo_no_da_lo_que_el_readme_afirma(modulo, tmp_path, monkeypatch, comando, cambio):
    python, _ = _entorno_falso(tmp_path)
    _con_ejecucion_falsa(modulo, monkeypatch, _salidas(tmp_path, **cambio))
    with pytest.raises(modulo.FalloDeInstalacion, match=f"({comando})"):
        modulo.comprobar_instalacion(python, tmp_path / "trabajo")
