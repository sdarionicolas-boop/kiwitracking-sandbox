"""La guía de uso: advertencias y códigos de salida contra el código (spec 006, RF-4 y RF-5)."""

import ast
import re
from pathlib import Path

import pytest

from kiwitracking import cli
from kiwitracking.cli import main

RAIZ = Path(__file__).resolve().parent.parent


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


def _codigos_del_programa():
    """Todo `Advertencia("CODIGO", …)` del paquete: el código es siempre un texto literal."""
    codigos = set()
    for archivo in (RAIZ / "kiwitracking").glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", None) == "Advertencia":
                assert nodo.args and isinstance(nodo.args[0], ast.Constant), f"{archivo.name}: código no literal"
                codigos.add(nodo.args[0].value)
    return codigos


def _filas_de_advertencias(guia):
    seccion = _seccion(guia, "## 5. Advertencias")
    return [
        (m.group(1), m.group(2).strip(), m.group(3).strip())
        for m in re.finditer(r"^\| `([A-Z_]+)` \|([^|]*)\|([^|]*)\|\s*$", seccion, re.M)
    ]


# --- Advertencias (RF-4) ------------------------------------------------------------------------------------------


def test_rf4_el_programa_emite_26_codigos_de_advertencia():
    assert len(_codigos_del_programa()) == 26


def test_rf4_cada_codigo_que_emite_el_programa_figura_en_la_guia(guia):
    en_la_guia = {codigo for codigo, _, _ in _filas_de_advertencias(guia)}
    sin_documentar = _codigos_del_programa() - en_la_guia
    assert sin_documentar == set(), f"advertencias sin documentar: {sorted(sin_documentar)}"


def test_rf4_la_guia_no_lista_codigos_que_el_programa_no_emite(guia):
    en_la_guia = {codigo for codigo, _, _ in _filas_de_advertencias(guia)}
    sobrantes = en_la_guia - _codigos_del_programa()
    assert sobrantes == set(), f"la guía lista advertencias que ya no existen: {sorted(sobrantes)}"


def test_rf4_ningun_codigo_aparece_dos_veces_en_la_tabla(guia):
    codigos = [codigo for codigo, _, _ in _filas_de_advertencias(guia)]
    assert len(codigos) == len(set(codigos))


def test_rf4_cada_fila_dice_que_significa_y_que_hacer(guia):
    for codigo, significado, que_hacer in _filas_de_advertencias(guia):
        assert len(significado) >= 25, f"{codigo}: falta explicar qué significa"
        assert len(que_hacer) >= 15, f"{codigo}: falta decir qué hacer"


def test_rf4_la_tabla_esta_en_orden_alfabetico_para_buscar_un_codigo(guia):
    codigos = [codigo for codigo, _, _ in _filas_de_advertencias(guia)]
    assert codigos == sorted(codigos)


def test_rf4_la_guia_explica_que_son_las_advertencias_y_donde_se_ven(guia):
    seccion = _seccion(guia, "## 5. Advertencias")
    for frase in ("no se detiene", "advertencias.json", "en pantalla", "código", "mensaje"):
        assert frase in seccion, f"falta explicar: {frase}"


def test_rf4_las_advertencias_que_cambian_resultados_se_distinguen(guia):
    seccion = _seccion(guia, "## 5. Advertencias")
    for codigo in ("NO_SIGNIFICATIVO", "HUELLA_NO_COINCIDE", "FALTA_CONFIRMACION", "SIN_ESTADO_FRIO", "DIAS_ESTIMADOS"):
        fila = next(f for f in _filas_de_advertencias(guia) if f[0] == codigo)
        assert fila[2], f"{codigo} no dice qué hacer"
    assert "sin corregir" in seccion or "no se corrigió" in seccion.lower()


# --- Códigos de salida (RF-5) -------------------------------------------------------------------------------------


def _filas_de_salida(guia):
    seccion = _seccion(guia, "## 6. Códigos de salida")
    return {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^\| (\d) \|([^|]*)\|\s*$", seccion, re.M)}


def test_rf5_la_guia_explica_los_codigos_0_1_2_y_3(guia):
    assert set(_filas_de_salida(guia)) == {0, 1, 2, 3}


def test_rf5_cada_codigo_dice_que_significa(guia):
    filas = _filas_de_salida(guia)
    assert "completó" in filas[0]
    assert "error de entrada" in filas[1]
    assert "uso incorrecto" in filas[2]
    assert "error inesperado" in filas[3]


def test_rf5_la_guia_explica_el_formato_de_los_mensajes_de_error(guia):
    seccion = _seccion(guia, "## 6. Códigos de salida")
    for frase in ("Error:", "Error inesperado:", "--depurar", "salida de errores"):
        assert frase in seccion, f"falta explicar: {frase}"


def test_rf5_los_codigos_de_la_guia_son_los_que_devuelve_el_programa(tmp_path, monkeypatch, capsys):
    assert main(["--version"]) == 0
    assert main(["kvpi", "--serie", str(tmp_path / "no_esta.csv"), "--muestreo", str(tmp_path / "x.csv")]) == 1
    assert main(["kvpi"]) == 2

    def fallar(*_a, **_k):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(cli, "ejecutar_kvpi", fallar)
    assert main(["kvpi", "--serie", "a.csv", "--muestreo", "b.csv"]) == 3
    err = capsys.readouterr().err
    assert "Error:" in err and "Error inesperado: RuntimeError" in err  # los formatos que la guía explica
