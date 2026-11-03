"""La guía de uso contra el programa (spec 006, RF-2 a RF-10): lo que afirma la guía se comprueba con el código."""

import argparse
import inspect
import re
import shlex
import tomllib
from pathlib import Path

import pytest

from kiwitracking.analisis import analizar
from kiwitracking.cli import construir_parser
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.flujo import ejecutar_kvpi

RAIZ = Path(__file__).resolve().parent.parent
VERSION = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


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


def _lineas_de_opciones(texto):
    """{opción: línea completa} para las líneas que empiezan con ``- `--opcion` ``."""
    return {m.group(1): m.group(0) for m in re.finditer(r"^- `(--[a-z0-9-]+)`.*$", texto, re.M)}


def _opciones_del_parser(comando):
    parser = construir_parser()
    if comando is None:
        return {o for a in parser._actions for o in a.option_strings if o.startswith("--")}
    subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return {o for a in subparsers.choices[comando]._actions for o in a.option_strings if o.startswith("--")}


def _obligatorias_del_parser(comando):
    subparsers = next(a for a in construir_parser()._actions if isinstance(a, argparse._SubParsersAction))
    return {a.option_strings[0] for a in subparsers.choices[comando]._actions if a.required}


def _como_se_escribe(valor):
    if isinstance(valor, (tuple, list)):
        return " ".join(_como_se_escribe(v) for v in valor)
    return str(valor)


def _por_defecto_esperado(comando):
    """{opción: valor por defecto escrito como se tipea}, sacado de las firmas del código."""
    firma = inspect.signature(analizar).parameters
    clima = ParametrosClima()
    kvpi = inspect.signature(ejecutar_kvpi).parameters
    esperado = {
        "kvpi": {
            "--salida": "plantas_kvpi.csv",
            "--min-campanas": kvpi["min_campanas"].default,
            "--cobertura-minima-campana": kvpi["cobertura_minima_campana"].default,
        },
        "mapa": {"--salida": "mapa.html"},
        "analizar": {
            "--salida": "resultados",
            "--correccion": firma["correccion"].default,
            "--prueba-t": firma["prueba_t"].default,
            "--alfa": firma["alfa"].default,
            "--min-plantas-grupo": firma["min_plantas_grupo"].default,
            "--p-ambiente": firma["p_ambiente"].default,
            "--p-estabilidad": firma["p_estabilidad"].default,
            "--ventana-frio": clima.ventana_frio,
            "--cobertura-minima": clima.cobertura_minima,
            "--max-hueco-dias": clima.max_hueco_dias,
            "--origenes-estimados": ",".join(clima.origenes_estimados),
        },
    }
    return {opcion: _como_se_escribe(valor) for opcion, valor in esperado[comando].items()}


COMANDOS = ["kvpi", "mapa", "analizar"]


# --- T6.5: instalación, recorrido y opciones (RF-2 parcial, RF-3, RF-10) -------------------------------------------


def test_rf2_la_guia_tiene_las_secciones_de_instalacion_y_recorrido(guia):
    posiciones = [guia.index(f"## {t}") for t in ("1. Requisitos e instalación", "2. Recorrido completo")]
    assert posiciones == sorted(posiciones)


def test_rf2_la_instalacion_dice_que_se_necesita_y_como_comprobar_la_version(guia):
    seccion = _seccion(guia, "## 1. Requisitos e instalación")
    assert "Python 3.14" in seccion and "Windows 11" in seccion
    assert "pip install" in seccion
    assert "kiwitracking --version" in _comandos_de_ejemplo(seccion)  # el comando de comprobación está en un bloque


def test_rf2_las_versiones_que_cita_la_guia_son_la_del_paquete(guia):
    citadas = set(re.findall(r"kiwitracking-(\d+\.\d+\.\d+)", guia)) | set(re.findall(r"kiwitracking (\d+\.\d+\.\d+)", guia))
    assert citadas <= {VERSION}, f"la guía cita versiones {sorted(citadas)} y el paquete es {VERSION}"


def test_rf2_el_recorrido_presenta_los_tres_comandos_en_orden(guia):
    seccion = _seccion(guia, "## 2. Recorrido completo")
    posiciones = [seccion.index(f"### `{c}`") for c in COMANDOS]
    assert posiciones == sorted(posiciones)
    assert "### Opciones generales" in seccion


@pytest.mark.parametrize("comando", COMANDOS)
def test_rf3_las_opciones_de_cada_comando_son_las_del_analizador(guia, comando):
    seccion = _seccion(guia, f"### `{comando}`")
    documentadas = set(_lineas_de_opciones(seccion))
    del_parser = _opciones_del_parser(comando) - {"--help"}
    assert del_parser - documentadas == set(), f"{comando}: opciones sin documentar {sorted(del_parser - documentadas)}"
    assert documentadas - del_parser == set(), f"{comando}: la guía nombra opciones que no existen {sorted(documentadas - del_parser)}"


def test_rf3_las_opciones_generales_son_help_y_version(guia):
    seccion = _seccion(guia, "### Opciones generales")
    assert set(_lineas_de_opciones(seccion)) == _opciones_del_parser(None) == {"--help", "--version"}


@pytest.mark.parametrize("comando", COMANDOS)
def test_rf3_las_opciones_con_valor_por_defecto_lo_indican_como_el_codigo(guia, comando):
    lineas = _lineas_de_opciones(_seccion(guia, f"### `{comando}`"))
    esperados = _por_defecto_esperado(comando)
    for opcion, valor in esperados.items():
        assert lineas[opcion].rstrip().endswith(f"(por defecto: {valor})"), f"{comando} {opcion}: {lineas[opcion]!r}"
    for opcion, linea in lineas.items():
        if opcion not in esperados:
            assert "(por defecto:" not in linea, f"{comando} {opcion} no tiene valor por defecto en el código: {linea!r}"


@pytest.mark.parametrize("comando", COMANDOS)
def test_rf3_las_opciones_obligatorias_se_marcan(guia, comando):
    lineas = _lineas_de_opciones(_seccion(guia, f"### `{comando}`"))
    obligatorias = _obligatorias_del_parser(comando) | ({"--huella"} if comando == "analizar" else set())
    for opcion in obligatorias:
        assert "(obligatoria)" in lineas[opcion], f"{comando} {opcion} es obligatoria"
    for opcion, linea in lineas.items():
        if opcion not in obligatorias:
            assert "(obligatoria)" not in linea, f"{comando} {opcion} no es obligatoria"


def test_rf3_la_guia_explica_los_valores_permitidos_de_las_opciones_con_lista(guia):
    seccion = _seccion(guia, "### `analizar`")
    for valor in ("auto", "forzar", "desactivar", "welch", "student", "invierno", "temporada", "Deficiente", "Adecuado", "Óptimo"):
        assert valor in seccion, f"falta explicar el valor {valor!r}"


def _comandos_de_ejemplo(guia):
    bloques = re.findall(r"```bash\n(.*?)```", guia, re.S)
    return [linea.strip() for bloque in bloques for linea in bloque.splitlines() if linea.strip().startswith("kiwitracking ")]


def test_rf3_la_guia_tiene_un_ejemplo_por_cada_comando(guia):
    ejemplos = _comandos_de_ejemplo(guia)
    for comando in COMANDOS:
        assert any(e.split()[1] == comando for e in ejemplos), f"falta un ejemplo de {comando}"


def test_rf3_cada_ejemplo_de_la_guia_es_aceptado_por_el_analizador_de_argumentos(guia):
    for ejemplo in _comandos_de_ejemplo(guia):
        argumentos = shlex.split(ejemplo)[1:]
        try:
            construir_parser().parse_args(argumentos)
        except SystemExit as salida:
            if salida.code != 0:  # `--help` y `--version` terminan con 0 y son ejemplos válidos
                pytest.fail(f"el analizador rechaza el ejemplo (código {salida.code}): {ejemplo}")


def test_rf10_los_ejemplos_van_en_una_sola_linea_y_con_barras_comunes(guia):
    for bloque in re.findall(r"```bash\n(.*?)```", guia, re.S):
        assert "\\\n" not in bloque and "`\n" not in bloque, "los comandos no llevan continuación de línea"
        assert "\\" not in bloque, "las rutas de los ejemplos llevan barras comunes"


def test_rf10_la_guia_no_trae_rutas_del_equipo_de_quien_la_escribio(guia):
    for patron in (r"[A-Za-z]:\\", r"[A-Za-z]:/Users", r"/Users/", r"/home/", r"sdari", r"AppData", r"Desktop"):
        assert not re.search(patron, guia), f"la guía contiene una ruta personal: {patron}"
