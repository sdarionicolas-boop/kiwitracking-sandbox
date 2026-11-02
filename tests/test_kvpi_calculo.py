"""T4.2: cálculo por planta (RF-7 a RF-10 de la spec 004, criterio 2)."""

import numpy as np
import pandas as pd
import pytest

from kiwitracking.kvpi import agregar_kvpi
from kiwitracking.resultado import ErrorDeEntrada

NAN = None


def _serie(filas):
    return pd.DataFrame(filas, columns=["id", "campaña", "KVPI"])


# Valores calculados a mano:
#  A: 0.2, 0.4, 0.6 -> media 0.4, desvío muestral 0.2, CV 0.5
#  B: 0.5 y una campaña vacía -> una sola campaña
#  C: todas vacías
#  D: 1.0 y -1.0 -> media 0 (CV vacío), desvío muestral raíz de 2
#  E: 0.3 y 0.5 -> media 0.4, desvío muestral raíz de 0.02
SERIE_A_MANO = _serie(
    [
        ("A", "c1", 0.2), ("A", "c2", 0.4), ("A", "c3", 0.6),
        ("B", "c1", 0.5), ("B", "c2", NAN), ("B", "c3", NAN),
        ("C", "c1", NAN), ("C", "c2", NAN), ("C", "c3", NAN),
        ("D", "c1", 1.0), ("D", "c2", -1.0), ("D", "c3", NAN),
        ("E", "c1", 0.3), ("E", "c2", 0.5), ("E", "c3", NAN),
    ]
)  # fmt: skip


def _por_id(resultado):
    return resultado.tabla.set_index("id")


def test_rf7_columnas_y_orden_por_id():
    resultado = agregar_kvpi(SERIE_A_MANO)
    assert list(resultado.tabla.columns) == ["id", "n_campanas", "KVPI_mean", "KVPI_std", "KVPI_cv"]
    assert list(resultado.tabla["id"]) == ["A", "B", "C", "D", "E"]


def test_rf7_n_campanas_cuenta_solo_las_campanas_con_dato():
    n = _por_id(agregar_kvpi(SERIE_A_MANO))["n_campanas"]
    assert n.to_dict() == {"A": 3, "B": 1, "C": 0, "D": 2, "E": 2}
    assert pd.api.types.is_integer_dtype(n)


def test_rf7_kvpi_mean_es_el_promedio_de_las_campanas_con_dato():
    media = _por_id(agregar_kvpi(SERIE_A_MANO))["KVPI_mean"]
    assert media["A"] == pytest.approx(0.4, abs=1e-15)
    assert media["B"] == pytest.approx(0.5, abs=1e-15)
    assert media["D"] == pytest.approx(0.0, abs=1e-15)
    assert media["E"] == pytest.approx(0.4, abs=1e-15)


def test_rf7_planta_sin_ninguna_campana_con_dato_tiene_promedio_vacio_y_n_cero():
    fila = _por_id(agregar_kvpi(SERIE_A_MANO)).loc["C"]
    assert fila["n_campanas"] == 0
    assert np.isnan(fila["KVPI_mean"])
    assert np.isnan(fila["KVPI_std"])
    assert np.isnan(fila["KVPI_cv"])


def test_rf8_kvpi_std_es_el_desvio_muestral_con_divisor_n_menos_1():
    desvio = _por_id(agregar_kvpi(SERIE_A_MANO))["KVPI_std"]
    assert desvio["A"] == pytest.approx(0.2, abs=1e-15)
    assert desvio["D"] == pytest.approx(np.sqrt(2.0), abs=1e-15)
    assert desvio["E"] == pytest.approx(np.sqrt(0.02), abs=1e-15)


def test_rf8_con_una_sola_campana_el_desvio_y_el_cv_quedan_vacios_y_el_promedio_no():
    fila = _por_id(agregar_kvpi(SERIE_A_MANO)).loc["B"]
    assert fila["KVPI_mean"] == pytest.approx(0.5)
    assert np.isnan(fila["KVPI_std"])
    assert np.isnan(fila["KVPI_cv"])


def test_rf8_coincide_con_numpy_en_datos_aleatorios():
    azar = np.random.default_rng(7)
    filas = [(planta, f"c{k}", float(azar.uniform(0.1, 0.9))) for planta in range(20) for k in range(6)]
    por_id = _por_id(agregar_kvpi(_serie(filas)))
    for planta in range(20):
        valores = np.array([v for p, _, v in filas if p == planta])
        assert por_id.loc[str(planta), "KVPI_mean"] == pytest.approx(valores.mean(), abs=1e-14)
        assert por_id.loc[str(planta), "KVPI_std"] == pytest.approx(valores.std(ddof=1), abs=1e-14)


def test_rf8_min_campanas_3_deja_vacio_el_desvio_de_quien_tiene_menos_pero_conserva_el_promedio():
    por_id = _por_id(agregar_kvpi(SERIE_A_MANO, min_campanas=3))
    assert por_id.loc["A", "KVPI_std"] == pytest.approx(0.2, abs=1e-15)
    for planta in ("D", "E"):
        assert np.isnan(por_id.loc[planta, "KVPI_std"])
        assert np.isnan(por_id.loc[planta, "KVPI_cv"])
    assert por_id.loc["E", "KVPI_mean"] == pytest.approx(0.4, abs=1e-15)
    assert por_id.loc["B", "KVPI_mean"] == pytest.approx(0.5, abs=1e-15)


def test_rf8_el_valor_por_defecto_de_min_campanas_es_2():
    assert not np.isnan(_por_id(agregar_kvpi(SERIE_A_MANO)).loc["E", "KVPI_std"])


def test_rf9_kvpi_cv_es_el_desvio_sobre_el_promedio():
    cv = _por_id(agregar_kvpi(SERIE_A_MANO))["KVPI_cv"]
    assert cv["A"] == pytest.approx(0.5, abs=1e-15)
    assert cv["E"] == pytest.approx(np.sqrt(0.02) / 0.4, abs=1e-15)


def test_rf9_con_promedio_cero_el_cv_queda_vacio():
    fila = _por_id(agregar_kvpi(SERIE_A_MANO)).loc["D"]
    assert fila["KVPI_std"] == pytest.approx(np.sqrt(2.0))
    assert np.isnan(fila["KVPI_cv"])


def test_rf9_con_promedio_negativo_el_cv_conserva_el_signo():
    serie = _serie([("N", "c1", -0.2), ("N", "c2", -0.6)])
    fila = _por_id(agregar_kvpi(serie)).loc["N"]
    assert fila["KVPI_mean"] == pytest.approx(-0.4)
    assert fila["KVPI_cv"] == pytest.approx(np.sqrt(0.08) / -0.4)


@pytest.mark.parametrize("valor", [1, 0, -3, 2.0, 2.5, "2", None, True])
def test_rf10_min_campanas_no_permitido_da_error_con_los_valores_permitidos(valor):
    with pytest.raises(ErrorDeEntrada, match="entero mayor o igual que 2"):
        agregar_kvpi(SERIE_A_MANO, min_campanas=valor)


@pytest.mark.parametrize("valor", [2, 3, 6, np.int64(4)])
def test_rf10_acepta_enteros_de_2_en_adelante(valor):
    agregar_kvpi(SERIE_A_MANO, min_campanas=valor)


def test_el_resultado_no_depende_del_orden_de_las_filas():
    esperado = agregar_kvpi(SERIE_A_MANO).tabla
    for semilla in range(5):
        barajada = SERIE_A_MANO.sample(frac=1, random_state=semilla).reset_index(drop=True)
        pd.testing.assert_frame_equal(agregar_kvpi(barajada).tabla, esperado)


def test_no_modifica_la_serie_de_entrada():
    copia = SERIE_A_MANO.copy()
    agregar_kvpi(SERIE_A_MANO)
    pd.testing.assert_frame_equal(SERIE_A_MANO, copia)


def test_los_errores_de_validacion_de_la_serie_llegan_al_usuario():
    with pytest.raises(ErrorDeEntrada, match="Faltan columnas"):
        agregar_kvpi(pd.DataFrame({"id": [1]}))


def test_las_advertencias_de_la_validacion_se_devuelven():
    serie = _serie([("A", "c1", 0.2), ("A", "c1", 0.2), ("A", "c2", 0.4)])
    resultado = agregar_kvpi(serie)
    assert [a.codigo for a in resultado.advertencias] == ["KVPI_DUPLICADO"]
    assert _por_id(resultado).loc["A", "n_campanas"] == 2


def _codigos(resultado):
    return [a.codigo for a in resultado.advertencias]


def _aviso(resultado, codigo):
    return next(a for a in resultado.advertencias if a.codigo == codigo).mensaje


def test_rf11_plantas_con_menos_campanas_que_las_encontradas_avisan_con_cantidad_y_rango():
    resultado = agregar_kvpi(SERIE_A_MANO)
    assert "PLANTAS_CON_MENOS_CAMPANAS" in _codigos(resultado)
    mensaje = _aviso(resultado, "PLANTAS_CON_MENOS_CAMPANAS")
    assert "4 plantas" in mensaje  # B, C, D y E
    assert "3 de la serie" in mensaje
    assert "entre 0 y 2" in mensaje


def test_rf11_una_planta_usa_el_singular():
    serie = _serie([("A", "c1", 0.2), ("A", "c2", 0.4), ("B", "c1", 0.5), ("B", "c2", NAN)])
    mensaje = _aviso(agregar_kvpi(serie), "PLANTAS_CON_MENOS_CAMPANAS")
    assert "1 planta " in mensaje
    assert "entre 1 y 1" in mensaje


def test_rf11_sin_plantas_incompletas_no_avisa():
    serie = _serie([("A", "c1", 0.2), ("A", "c2", 0.4), ("B", "c1", 0.5), ("B", "c2", 0.1)])
    assert agregar_kvpi(serie).advertencias == []


def test_rf11_una_campana_con_todo_vacio_igual_cuenta_como_encontrada():
    serie = _serie(
        [("A", "c1", 0.2), ("A", "c2", 0.4), ("A", "c3", NAN), ("B", "c1", 0.5), ("B", "c2", 0.1), ("B", "c3", NAN)]
    )
    mensaje = _aviso(agregar_kvpi(serie), "PLANTAS_CON_MENOS_CAMPANAS")
    assert "2 plantas" in mensaje
    assert "3 de la serie" in mensaje


def test_rf11_con_una_sola_campana_en_toda_la_serie_no_avisa_menos_campanas():
    serie = _serie([("A", "c1", 0.2), ("B", "c1", 0.5)])
    assert _codigos(agregar_kvpi(serie)) == ["SIN_DESVIO"]


def test_rf12_plantas_con_desvio_vacio_por_min_campanas_avisan_con_la_cantidad():
    mensaje = _aviso(agregar_kvpi(SERIE_A_MANO), "SIN_DESVIO")
    assert "2 plantas" in mensaje  # B y C
    assert "menos de 2 campañas" in mensaje


def test_rf12_el_umbral_es_min_campanas():
    mensaje = _aviso(agregar_kvpi(SERIE_A_MANO, min_campanas=3), "SIN_DESVIO")
    assert "4 plantas" in mensaje  # B, C, D y E
    assert "menos de 3 campañas" in mensaje


def test_rf12_una_planta_usa_el_singular():
    serie = _serie([("A", "c1", 0.2), ("A", "c2", 0.4), ("B", "c1", 0.5), ("B", "c2", NAN)])
    assert "1 planta " in _aviso(agregar_kvpi(serie), "SIN_DESVIO")


def test_rf12_sin_plantas_sin_desvio_no_avisa():
    serie = _serie([("A", "c1", 0.2), ("A", "c2", 0.4)])
    assert "SIN_DESVIO" not in _codigos(agregar_kvpi(serie))


def test_las_advertencias_salen_en_orden_validacion_menos_campanas_sin_desvio():
    serie = _serie([("A", "c1", 0.2), ("A", "c1", 0.2), ("A", "c2", 0.4), ("B", "c1", 0.5), ("B", "c2", NAN)])
    assert _codigos(agregar_kvpi(serie)) == ["KVPI_DUPLICADO", "PLANTAS_CON_MENOS_CAMPANAS", "SIN_DESVIO"]
