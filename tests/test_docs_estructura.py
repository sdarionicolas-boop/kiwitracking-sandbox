"""La guía de uso completa: sus nueve secciones en orden, cómo generar los paquetes y los límites (spec 006, RF-2 y RF-9)."""

import re
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.kvpi import agregar_kvpi

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "tests" / "golden"
ENCABEZADOS = [
    "## 1. Requisitos e instalación",
    "## 2. Recorrido completo",
    "## 3. Formatos de los archivos de entrada",
    "## 4. Archivos de salida",
    "## 5. Advertencias",
    "## 6. Códigos de salida",
    "## 7. Reproducir los resultados de la tesis",
    "## 8. Generar los paquetes",
    "## 9. Límites del programa",
]


@pytest.fixture(scope="module")
def guia():
    return (RAIZ / "docs" / "uso.md").read_text(encoding="utf-8")


def _seccion(texto, encabezado):
    """El texto entre un encabezado y el siguiente del mismo nivel o superior."""
    nivel = len(encabezado) - len(encabezado.lstrip("#"))
    coincidencia = re.search(rf"^{re.escape(encabezado)}\s*$", texto, re.M)
    assert coincidencia, f"falta el encabezado {encabezado!r}"
    resto = texto[coincidencia.end():]
    siguiente = re.search(rf"^#{{1,{nivel}}} ", resto, re.M)
    return resto[: siguiente.start()] if siguiente else resto


# --- Estructura (RF-2) --------------------------------------------------------------------------------------------


def test_rf2_la_guia_tiene_exactamente_los_nueve_encabezados_en_el_orden_de_la_spec(guia):
    encontrados = re.findall(r"^## .*$", guia, re.M)
    assert encontrados == ENCABEZADOS


def test_rf2_la_guia_empieza_con_su_titulo_y_no_es_un_borrador(guia):
    assert guia.startswith("# Guía de uso de KiwiTracking")
    assert "Borrador" not in guia and "borrador" not in guia


# --- Generar los paquetes (RF-2) ----------------------------------------------------------------------------------


def test_rf2_generar_los_paquetes_explica_la_instalacion_de_desarrollo_y_la_construccion(guia):
    seccion = _seccion(guia, "## 8. Generar los paquetes")
    comandos = [linea.strip() for bloque in re.findall(r"```bash\n(.*?)```", seccion, re.S) for linea in bloque.splitlines()]
    for comando in ('pip install -e ".[dev]"', "python -m pytest -W error", "python -m build", "python scripts/probar_instalacion.py"):
        assert comando in comandos, f"falta el comando en un bloque de código: {comando}"
    for frase in ("dist/", "wheel", "sdist", "pytest"):
        assert frase in seccion, f"falta explicar: {frase}"


def test_rf2_generar_los_paquetes_advierte_del_egg_info_desactualizado(guia):
    seccion = _seccion(guia, "## 8. Generar los paquetes")
    assert "kiwitracking.egg-info" in seccion
    assert "borrá" in seccion.lower() or "borrar" in seccion.lower()


def test_rf2_generar_los_paquetes_explica_la_prueba_de_instalacion_en_un_entorno_limpio(guia):
    seccion = _seccion(guia, "## 8. Generar los paquetes")
    for frase in ("scripts/probar_instalacion.py", "entorno", "internet"):
        assert frase in seccion


def test_rf2_generar_los_paquetes_explica_que_lleva_cada_archivo(guia):
    seccion = _seccion(guia, "## 8. Generar los paquetes")
    assert "tests/golden/" in seccion and "no lleva" in seccion


def test_rf2_generar_los_paquetes_explica_como_cambiar_la_version(guia):
    seccion = _seccion(guia, "## 8. Generar los paquetes")
    for frase in ("pyproject.toml", "CITATION.cff", "reinstal"):
        assert frase in seccion


# --- Límites del programa (RF-9) ----------------------------------------------------------------------------------


def test_rf9_dice_que_el_paso_de_earth_engine_no_es_parte_del_programa(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    for frase in ("Google Earth Engine", "no lo hace", "COPERNICUS/S2_SR_HARMONIZED", "mediana"):
        assert frase in seccion, f"falta decir: {frase}"


def test_rf9_explica_la_diferencia_entre_la_prueba_por_defecto_y_la_de_la_tesis(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    for frase in ("Welch", "Student", "--prueba-t student"):
        assert frase in seccion


def test_rf9_explica_los_dias_interpolados_con_las_cifras_del_archivo(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    clima = pd.read_csv(GOLDEN / "clima_diario.csv")
    interpolados = int((clima["origen"] == "interpolado").sum())
    assert interpolados == 58 and "58" in seccion
    for frase in ("26 de 123", "DIAS_ESTIMADOS", "no se excluyen"):
        assert frase in seccion


def test_rf9_dice_que_el_mapa_necesita_internet_para_el_fondo_satelital(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    assert "internet" in seccion and "--sin-fondo-satelital" in seccion


def test_rf9_dice_donde_se_probo_y_que_no_se_probo(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    for frase in ("Windows 11", "Python 3.14", "no se probó"):
        assert frase in seccion
    for sistema in ("Linux", "macOS"):
        if sistema in guia:
            oraciones = [o for o in re.split(r"(?<=[.!?])\s+", guia) if sistema in o]
            assert all("no se probó" in o or "no está verificado" in o for o in oraciones), oraciones


def test_rf9_dice_que_la_version_no_tiene_doi_propio_y_donde_esta_la_cita(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    for frase in ("La versión 1.2.0 todavía no tiene DOI propio", "(`10.5281/zenodo.19352552`) es el del proyecto", "CITATION.cff"):
        assert frase in seccion


def test_rf9_dice_que_esta_verificado_con_cifras_que_los_datos_confirman(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    serie = pd.read_csv(GOLDEN / "kvpi_serie.csv")
    publicado = pd.read_csv(GOLDEN / "datos_plantas_completos.csv").assign(id=lambda t: t["id"].astype(str))
    obtenido = agregar_kvpi(serie).tabla.set_index("id")
    esperado = publicado.set_index("id")
    assert len(publicado) == 159 and "159 plantas" in seccion
    assert (obtenido["KVPI_mean"] - esperado["KVPI_mean"]).abs().max() < 1e-12
    assert (obtenido["KVPI_std"] - esperado["KVPI_std"]).abs().max() < 1e-12
    assert "1e-12" in seccion


def test_rf9_dice_lo_que_no_esta_verificado(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    for frase in ("con otros lotes, otros cultivos u otras mallas no está verificado", "Se supone que un punto sin píxel válido", "--campanas"):
        assert frase in seccion


def test_rf9_dice_que_los_mensajes_de_uso_pueden_salir_en_ingles(guia):
    seccion = _seccion(guia, "## 9. Límites del programa")
    assert "pueden salir en inglés" in seccion


def test_rf9_no_afirma_garantias_que_nadie_comprobo(guia):
    for palabra in ("garantiza", "siempre funciona", "cualquier sistema", "sin errores", "100 % seguro"):
        assert palabra not in guia.lower(), f"afirmación sin respaldo: {palabra}"
