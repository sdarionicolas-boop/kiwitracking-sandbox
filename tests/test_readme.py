"""El README del repositorio: qué dice y que su ejemplo mínimo funciona (spec 006, RF-1 y RF-10)."""

import contextlib
import io
import re
import shlex
import shutil
import tempfile
import tomllib
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.cli import main

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "tests" / "golden"
VERSION = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
ENCABEZADOS = [
    "## Qué hace",
    "## Qué no hace",
    "## Instalación",
    "## Ejemplo mínimo",
    "## Guía completa",
    "## Cómo citar",
    "## Licencia",
]


@pytest.fixture(scope="module")
def readme():
    return (RAIZ / "README.md").read_text(encoding="utf-8")


def _seccion(texto, encabezado):
    nivel = len(encabezado) - len(encabezado.lstrip("#"))
    coincidencia = re.search(rf"^{re.escape(encabezado)}\s*$", texto, re.M)
    assert coincidencia, f"falta el encabezado {encabezado!r}"
    resto = texto[coincidencia.end():]
    siguiente = re.search(rf"^#{{1,{nivel}}} ", resto, re.M)
    return resto[: siguiente.start()] if siguiente else resto


# --- Contenido (RF-1) ---------------------------------------------------------------------------------------------


def test_rf1_el_readme_tiene_titulo_y_las_siete_secciones_en_orden(readme):
    assert readme.startswith("# KiwiTracking")
    assert re.findall(r"^## .*$", readme, re.M) == ENCABEZADOS


def test_rf1_el_readme_no_es_un_borrador(readme):
    assert "borrador" not in readme.lower() and "T6.10" not in readme


def test_rf1_dice_que_hace_el_programa(readme):
    seccion = _seccion(readme, "## Qué hace")
    for frase in ("kvpi", "mapa", "analizar", "KVPI", "malla", "ambientes", "Mantener", "Observar", "Intervenir"):
        assert frase in seccion, f"falta decir: {frase}"


def test_rf1_dice_que_no_hace_el_programa(readme):
    seccion = _seccion(readme, "## Qué no hace")
    for frase in ("Google Earth Engine", "otros lotes", "no está verificado"):
        assert frase in seccion, f"falta decir: {frase}"


def test_rf1_explica_la_instalacion_con_lo_que_se_probo(readme):
    seccion = _seccion(readme, "## Instalación")
    for frase in ("Python 3.14", "Windows 11", "pip install", "kiwitracking --version"):
        assert frase in seccion, f"falta explicar: {frase}"


def test_rf1_apunta_a_la_guia_completa_y_el_enlace_existe(readme):
    seccion = _seccion(readme, "## Guía completa")
    enlaces = re.findall(r"\]\(([^)]+)\)", seccion)
    assert "docs/uso.md" in enlaces
    for enlace in enlaces:
        if not enlace.startswith("http"):
            assert (RAIZ / enlace).exists(), f"el enlace no existe: {enlace}"


def test_rf1_dice_como_citarlo_y_remite_al_citation_cff(readme):
    seccion = _seccion(readme, "## Cómo citar")
    for frase in ("CITATION.cff", VERSION, "todavía no tiene DOI propio", "tesis"):
        assert frase in seccion, f"falta decir: {frase}"
    assert "[CITATION.cff](CITATION.cff)" in seccion  # un enlace, no solo el nombre
    assert (RAIZ / "CITATION.cff").exists()


def test_rf1_dice_la_licencia_y_el_enlace_existe(readme):
    seccion = _seccion(readme, "## Licencia")
    assert "MIT" in seccion and "(LICENSE)" in seccion
    assert (RAIZ / "LICENSE").exists()


def test_rf1_las_versiones_que_cita_son_la_del_paquete(readme):
    citadas = set(re.findall(r"kiwitracking-(\d+\.\d+\.\d+)", readme)) | set(re.findall(r"kiwitracking (\d+\.\d+\.\d+)", readme))
    assert citadas <= {VERSION}


def test_rf10_el_readme_no_trae_rutas_del_equipo_de_quien_lo_escribio(readme):
    for patron in (r"[A-Za-z]:\\", r"[A-Za-z]:/Users", r"/Users/", r"/home/", r"sdari", r"AppData", r"Desktop"):
        assert not re.search(patron, readme), f"el README contiene una ruta personal: {patron}"


def test_rf10_los_comandos_del_readme_van_en_una_sola_linea(readme):
    for bloque in re.findall(r"```bash\n(.*?)```", readme, re.S):
        assert "\\" not in bloque and "`\n" not in bloque


def test_rf1_no_afirma_garantias_que_nadie_comprobo(readme):
    for palabra in ("garantiza", "siempre funciona", "cualquier sistema", "sin errores"):
        assert palabra not in readme.lower()


# --- El ejemplo mínimo se ejecuta (RF-1) --------------------------------------------------------------------------


def _ejemplo(readme):
    coincidencia = re.search(r"<!-- prueba: ejemplo-minimo -->\s*```bash\n(.*?)```", _seccion(readme, "## Ejemplo mínimo"), re.S)
    assert coincidencia, "el ejemplo mínimo no está en un bloque marcado"
    return [linea.strip() for linea in coincidencia.group(1).splitlines() if linea.strip()]


@pytest.fixture(scope="module")
def corrida(readme):
    """Arma en una carpeta temporal los archivos de ejemplo que nombra el README y corre el ejemplo."""
    carpeta = Path(tempfile.mkdtemp(prefix="readme_"))
    publicado = pd.read_csv(GOLDEN / "datos_plantas_completos.csv")
    publicado[["id", "X", "Y"]].to_csv(carpeta / "muestreo.csv", index=False)
    shutil.copy(GOLDEN / "kvpi_serie.csv", carpeta / "serie.csv")
    shutil.copy(GOLDEN / "malla_zona.geojson", carpeta / "malla.geojson")
    shutil.copy(GOLDEN / "clima_diario.csv", carpeta / "clima_diario.csv")
    pantallas, codigos, huella = [], [], None
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(carpeta)
        for linea in _ejemplo(readme):
            assert linea.startswith("kiwitracking "), f"no es un comando: {linea}"
            if huella is not None:
                linea = linea.replace("HUELLA", huella)
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigos.append(main(shlex.split(linea)[1:]))
            pantallas.append(salida.getvalue())
            encontrada = re.search(r"^Huella: ([0-9a-f]{12})$", pantallas[-1], re.M)
            huella = encontrada.group(1) if encontrada else huella
    yield {"carpeta": carpeta, "pantallas": pantallas, "codigos": codigos, "huella": huella}
    shutil.rmtree(carpeta, ignore_errors=True)


def test_rf1_el_ejemplo_minimo_tiene_los_tres_comandos_en_orden(readme):
    comandos = [linea.split()[1] for linea in _ejemplo(readme)]
    assert comandos == ["kvpi", "mapa", "analizar"]


def test_rf1_el_ejemplo_minimo_termina_con_codigo_0_en_los_tres_comandos(corrida):
    assert corrida["codigos"] == [0, 0, 0]


def test_rf1_el_ejemplo_minimo_da_los_resultados_que_el_readme_afirma(corrida, readme):
    kvpi, mapa, analizar = corrida["pantallas"]
    assert "Plantas en el resultado: 159" in kvpi
    assert re.search(r"bajo malla: 53\b", mapa) and corrida["huella"] == "c4e55ae105c6"
    assert "Plantas analizadas: 159" in analizar
    assert "Estado de frío: Óptimo" in analizar
    seccion = _seccion(readme, "## Ejemplo mínimo")
    for texto in ("159", "53", "Óptimo"):
        assert texto in seccion


def test_rf1_el_ejemplo_minimo_deja_los_archivos_que_el_readme_dice(corrida):
    carpeta = corrida["carpeta"]
    for nombre in ("plantas_kvpi.csv", "mapa.html", "resultados/plantas.csv", "resultados/resumen.json", "resultados/advertencias.json"):
        assert (carpeta / nombre).is_file(), nombre


def test_rf1_el_ejemplo_minimo_no_usa_la_red(readme):
    assert "--sin-fondo-satelital" in " ".join(_ejemplo(readme))
