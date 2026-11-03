"""La sección «Reproducir los resultados de la tesis» de la guía: se ejecutan sus comandos y se comprueban sus números
(spec 006, RF-8).

Los bloques de la guía que se ejecutan van marcados con `<!-- prueba: nombre -->`. `HUELLA` se reemplaza por la huella
que imprimió el `mapa` anterior. Las rutas son relativas a la raíz del repositorio, así que se corre en una carpeta
temporal con una copia de `tests/golden/`.
"""

import contextlib
import io
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.cli import main

RAIZ = Path(__file__).resolve().parent.parent
ENCABEZADO = "## 7. Reproducir los resultados de la tesis"


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


def _bloques_marcados(texto):
    """{nombre: [líneas]} de los bloques ```bash precedidos por `<!-- prueba: nombre -->`."""
    bloques = {}
    for m in re.finditer(r"<!-- prueba: ([a-z-]+) -->\s*```bash\n(.*?)```", texto, re.S):
        bloques[m.group(1)] = [linea.strip() for linea in m.group(2).splitlines() if linea.strip()]
    return bloques


@pytest.fixture(scope="module")
def corrida(guia):
    """Ejecuta, en una carpeta temporal, todos los bloques marcados de la sección, en el orden de la guía."""
    bloques = _bloques_marcados(_seccion(guia, ENCABEZADO))
    assert bloques, "la sección no tiene bloques marcados"
    carpeta = Path(tempfile.mkdtemp(prefix="reproduccion_"))
    (carpeta / "tests").mkdir()
    shutil.copytree(RAIZ / "tests" / "golden", carpeta / "tests" / "golden")
    pantallas, resultados, huella = {}, {}, None
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(carpeta)
        for nombre, lineas in bloques.items():
            for linea in lineas:
                if huella is not None:
                    linea = linea.replace("HUELLA", huella)
                if linea.startswith("kiwitracking "):
                    salida = io.StringIO()
                    with contextlib.redirect_stdout(salida):
                        codigo = main(shlex.split(linea)[1:])
                    pantallas[nombre] = salida.getvalue()
                    resultados[nombre] = codigo
                    encontrada = re.search(r"^Huella: ([0-9a-f]{12})$", pantallas[nombre], re.M)
                    if encontrada:
                        huella = encontrada.group(1)
                elif linea.startswith("python -c "):
                    argumentos = shlex.split(linea)
                    proceso = subprocess.run([sys.executable, *argumentos[1:]], capture_output=True, text=True, cwd=carpeta)
                    pantallas[nombre] = proceso.stdout
                    resultados[nombre] = proceso.returncode
                else:
                    pytest.fail(f"{nombre}: la línea no es un comando que se pueda ejecutar: {linea}")
    yield {"carpeta": carpeta, "pantallas": pantallas, "codigos": resultados, "huella": huella, "bloques": bloques}
    shutil.rmtree(carpeta, ignore_errors=True)


def _json(corrida, carpeta, nombre):
    return json.loads((corrida["carpeta"] / carpeta / nombre).read_text(encoding="utf-8"))


def _cuentas(corrida, carpeta):
    return pd.read_csv(corrida["carpeta"] / carpeta / "plantas.csv")["recomendacion"].value_counts().to_dict()


# --- Estructura ----------------------------------------------------------------------------------------------------


def test_rf8_la_seccion_tiene_las_dos_partes_rotuladas(guia):
    seccion = _seccion(guia, ENCABEZADO)
    assert seccion.index("### Reproducir lo publicado") < seccion.index("### Lo que agrega el programa")


def test_rf8_la_seccion_dice_de_donde_salen_los_datos_y_que_el_wheel_no_los_trae(guia):
    seccion = _seccion(guia, ENCABEZADO)
    assert "Los datos de referencia están en `tests/golden/`" in seccion
    assert "en el repositorio y en el archivo `sdist`" in seccion
    assert "no en el `wheel`" in seccion


def test_rf8_la_segunda_parte_aclara_que_no_es_lo_publicado(guia):
    parte_2 = _seccion(guia, "### Lo que agrega el programa")
    assert "no es lo publicado" in parte_2
    assert "interpolad" in parte_2


def test_rf8_los_16_mantener_nunca_se_presentan_como_resultado_de_la_tesis(guia):
    parte_1 = _seccion(guia, "### Reproducir lo publicado")
    parte_2 = _seccion(guia, "### Lo que agrega el programa")
    patron = r"16\s+(?:de\s+)?\"?Mantener"
    assert re.search(patron, parte_2), "la parte 2 debe mostrar los 16 Mantener"
    fuera = guia.replace(parte_2, "")
    assert not re.search(patron, fuera), "los 16 Mantener solo pueden aparecer en la parte 2"
    assert not re.search(patron, parte_1)


def test_rf8_los_bloques_marcados_son_los_esperados(corrida):
    assert list(corrida["bloques"]) == [
        "publicado-mapa", "publicado-analizar", "publicado-comparar", "agrega-analizar", "agrega-sin-escalar",
    ]  # fmt: skip


def test_rf8_todos_los_comandos_de_la_guia_terminan_con_codigo_0(corrida):
    assert corrida["codigos"] == {nombre: 0 for nombre in corrida["bloques"]}


# --- Parte 1: lo publicado ------------------------------------------------------------------------------------------


def _parte_1(guia):
    return _seccion(guia, "### Reproducir lo publicado")


def _parte_2(guia):
    return _seccion(guia, "### Lo que agrega el programa")


def test_rf8_parte_1_el_mapa_da_53_bajo_malla_106_fuera_y_la_huella(corrida, guia):
    pantalla = corrida["pantallas"]["publicado-mapa"]
    assert re.search(r"bajo malla: 53\b", pantalla) and re.search(r"fuera de malla: 106\b", pantalla)
    assert corrida["huella"] == "c4e55ae105c6"
    for texto in ("53", "106", "c4e55ae105c6"):
        assert texto in _parte_1(guia)


def test_rf8_parte_1_el_factor_de_correccion_y_el_valor_p_con_student(corrida, guia):
    resumen = _json(corrida, "resultados_publicado", "resumen.json")
    assert resumen["resumen"]["fc"] == pytest.approx(1.2262, abs=5e-5)
    assert resumen["resumen"]["p_valor"] == pytest.approx(1.03e-26, rel=0.01)
    assert resumen["resumen"]["prueba_t"] == "student" and resumen["resumen"]["escalar_std"] is False
    for texto in ("1,2262", "1,0e-26"):
        assert texto in _parte_1(guia)


def test_rf8_parte_1_cero_mantener_y_19_intervenir(corrida, guia):
    cuentas = _cuentas(corrida, "resultados_publicado")
    assert (cuentas.get("Mantener", 0), cuentas["Intervenir"], cuentas["Observar"]) == (0, 19, 140)
    for texto in ("0 \"Mantener\"", "19 \"Intervenir\"", "140"):
        assert texto in _parte_1(guia)


def test_rf8_parte_1_el_resultado_es_el_del_csv_publicado(corrida):
    assert corrida["pantallas"]["publicado-comparar"].split() == ["True", "True", "True"]


def test_rf8_parte_1_el_resultado_publicado_se_comprueba_tambien_sin_pasar_por_la_guia(corrida):
    obtenido = pd.read_csv(corrida["carpeta"] / "resultados_publicado" / "plantas.csv")
    publicado = pd.read_csv(RAIZ / "tests" / "golden" / "datos_plantas_completos.csv")
    assert (obtenido["KVPI_corregido"] - publicado["KVPI_corregido"]).abs().max() < 1e-9
    assert obtenido["ambiente"].tolist() == publicado["ambiente"].tolist()
    assert obtenido["recomendacion"].tolist() == publicado["recomendacion"].tolist()


def test_rf8_parte_1_el_comando_de_comparacion_de_la_guia_detecta_una_diferencia(corrida):
    """Si el resultado difiere del publicado, el comando de la guía tiene que dar False (no puede dar True siempre)."""
    ruta = corrida["carpeta"] / "resultados_publicado" / "plantas.csv"
    original = ruta.read_text(encoding="utf-8")
    tabla = pd.read_csv(ruta)
    tabla.loc[0, "recomendacion"] = "Mantener" if tabla.loc[0, "recomendacion"] != "Mantener" else "Observar"
    tabla.loc[1, "KVPI_corregido"] += 0.01
    tabla.loc[2, "ambiente"] = "Otro"
    try:
        tabla.to_csv(ruta, index=False)
        comando = next(l for l in corrida["bloques"]["publicado-comparar"] if l.startswith("python -c "))
        proceso = subprocess.run([sys.executable, *shlex.split(comando)[1:]], capture_output=True, text=True, cwd=corrida["carpeta"])
        assert proceso.stdout.split() == ["False", "False", "False"]
    finally:
        ruta.write_text(original, encoding="utf-8")


def test_rf8_parte_1_el_estado_de_frio_es_el_escrito_a_mano(corrida):
    estado = _json(corrida, "resultados_publicado", "resumen.json")["estado_frio"]
    assert (estado["origen"], estado["estado"]) == ("manual", "Deficiente")


# --- Parte 2: lo que agrega el programa -----------------------------------------------------------------------------


def test_rf8_parte_2_estado_de_frio_optimo_de_2024_con_1128_8_horas(corrida, guia):
    estado = _json(corrida, "resultados_con_clima", "resumen.json")["estado_frio"]
    assert (estado["origen"], estado["estado"], estado["periodo"]) == ("clima", "Óptimo", 2024)
    assert estado["horas"] == pytest.approx(1128.8, abs=0.05) and estado["cobertura"] == 1.0
    for texto in ("Óptimo", "2024", "1.128,8"):
        assert texto in _parte_2(guia)


def test_rf8_parte_2_16_mantener_19_intervenir_y_124_observar(corrida, guia):
    cuentas = _cuentas(corrida, "resultados_con_clima")
    assert (cuentas["Mantener"], cuentas["Intervenir"], cuentas["Observar"]) == (16, 19, 124)
    for texto in ("16 \"Mantener\"", "19 \"Intervenir\"", "124"):
        assert texto in _parte_2(guia)


def test_rf8_parte_2_sin_escalar_el_desvio_da_15_mantener(corrida, guia):
    cuentas = _cuentas(corrida, "resultados_sin_escalar")
    assert (cuentas["Mantener"], cuentas["Intervenir"], cuentas["Observar"]) == (15, 19, 125)
    for texto in ("15 \"Mantener\"", "125"):
        assert texto in _parte_2(guia)


def test_rf8_parte_2_el_aviso_de_dias_estimados_dice_26_de_123(corrida, guia):
    avisos = _json(corrida, "resultados_con_clima", "advertencias.json")
    mensaje = next(a["mensaje"] for a in avisos if a["codigo"] == "DIAS_ESTIMADOS")
    assert "26 de 123" in mensaje and "21,1 %" in mensaje
    resumen = _json(corrida, "resultados_con_clima", "resumen.json")["estado_frio"]
    assert resumen["dias_estimados"] == 26
    for texto in ("26 de 123", "21,1 %"):
        assert texto in _parte_2(guia)


def test_rf8_parte_2_la_causa_de_la_diferencia_esta_comprobada(corrida):
    # la diferencia con lo publicado (0 «Mantener») es el estado de frío y el escalado del desvío, no otra cosa
    publicado = _cuentas(corrida, "resultados_publicado")
    sin_escalar = _cuentas(corrida, "resultados_sin_escalar")
    con_clima = _cuentas(corrida, "resultados_con_clima")
    assert publicado.get("Mantener", 0) == 0 and sin_escalar["Mantener"] == 15 and con_clima["Mantener"] == 16
    assert publicado["Intervenir"] == sin_escalar["Intervenir"] == con_clima["Intervenir"] == 19


def test_rf8_parte_2_con_la_prueba_por_defecto_el_valor_p_es_mas_chico(corrida, guia):
    resumen = _json(corrida, "resultados_con_clima", "resumen.json")["resumen"]
    assert resumen["prueba_t"] == "welch" and resumen["p_valor"] == pytest.approx(5.86e-35, rel=0.01)
    assert "5,9e-35" in guia
