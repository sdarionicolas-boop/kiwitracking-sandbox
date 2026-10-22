import pandas as pd
import pytest

from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.validacion import excluir_sin_kvpi, validar_parametros, validar_tabla


def _tabla_valida():
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "KVPI_mean": [0.50, 0.55, 0.45],
            "KVPI_std": [0.03, 0.04, 0.05],
            "bajo_malla": [0, 0, 1],
        }
    )


def test_rf1_tabla_valida_no_da_error():
    validar_tabla(_tabla_valida())


def test_rf1_falta_una_columna_obligatoria_y_el_error_la_nombra():
    tabla = _tabla_valida().drop(columns=["KVPI_std"])

    with pytest.raises(ErrorDeEntrada, match="KVPI_std"):
        validar_tabla(tabla)


def test_rf1_si_faltan_varias_columnas_el_error_las_nombra_todas():
    tabla = _tabla_valida().drop(columns=["KVPI_std", "bajo_malla"])

    with pytest.raises(ErrorDeEntrada) as error:
        validar_tabla(tabla)

    assert "KVPI_std" in str(error.value)
    assert "bajo_malla" in str(error.value)


def test_rf1_tabla_vacia_da_error():
    tabla = _tabla_valida().iloc[0:0]

    with pytest.raises(ErrorDeEntrada, match="vacía"):
        validar_tabla(tabla)


def test_rf1_kvpi_mean_con_texto_da_error_que_nombra_la_columna():
    tabla = _tabla_valida()
    tabla["KVPI_mean"] = ["0.50", "abc", "0.45"]

    with pytest.raises(ErrorDeEntrada, match="KVPI_mean.*numéric"):
        validar_tabla(tabla)


def test_rf1_kvpi_mean_con_valores_vacios_no_da_error_aca():
    # Los vacíos se tratan en RF-2 (exclusión con advertencia), no son un error de RF-1.
    tabla = _tabla_valida()
    tabla.loc[1, "KVPI_mean"] = float("nan")

    validar_tabla(tabla)


def test_rf1_no_modifica_la_tabla_de_entrada():
    tabla = _tabla_valida()
    copia = tabla.copy()

    validar_tabla(tabla)

    pd.testing.assert_frame_equal(tabla, copia)


# --- T3: parámetros y valores de bajo_malla ---------------------------------------------


@pytest.mark.parametrize("correccion", ["auto", "forzar", "desactivar"])
def test_rf14_correccion_con_valor_permitido_no_da_error(correccion):
    validar_parametros(correccion=correccion)


@pytest.mark.parametrize("correccion", ["Auto", "si", "", None])
def test_rf14_correccion_invalida_da_error_que_nombra_los_valores_permitidos(correccion):
    with pytest.raises(ErrorDeEntrada) as error:
        validar_parametros(correccion=correccion)

    for permitido in ("auto", "forzar", "desactivar"):
        assert permitido in str(error.value)


@pytest.mark.parametrize("estado", [None, "Deficiente", "Adecuado", "Óptimo"])
def test_rf5_estado_de_frio_permitido_o_ausente_no_da_error(estado):
    validar_parametros(estado_frio_ultima_campana=estado)


@pytest.mark.parametrize("estado", ["deficiente", "Optimo", "ÓPTIMO", "Ã“ptimo", ""])
def test_rf5_estado_de_frio_con_otra_mayuscula_o_tilde_da_error_con_los_permitidos(estado):
    with pytest.raises(ErrorDeEntrada) as error:
        validar_parametros(estado_frio_ultima_campana=estado)

    for permitido in ("Deficiente", "Adecuado", "Óptimo"):
        assert permitido in str(error.value)


def test_rf1_bajo_malla_con_un_valor_distinto_de_0_y_1_da_error():
    tabla = _tabla_valida()
    tabla.loc[1, "bajo_malla"] = 2

    with pytest.raises(ErrorDeEntrada, match="bajo_malla.*0 y 1"):
        validar_tabla(tabla)


def test_rf1_bajo_malla_vacio_da_error():
    tabla = _tabla_valida()
    tabla["bajo_malla"] = [0, float("nan"), 1]

    with pytest.raises(ErrorDeEntrada, match="bajo_malla"):
        validar_tabla(tabla)


def test_rf1_bajo_malla_solo_con_0_y_1_no_da_error():
    tabla = _tabla_valida()
    tabla["bajo_malla"] = [1, 1, 0]

    validar_tabla(tabla)


# --- T4: exclusión de plantas con KVPI vacío --------------------------------------------


def _tabla_con_dos_vacios():
    tabla = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "KVPI_mean": [0.50, float("nan"), 0.45, float("nan"), 0.52],
            "KVPI_std": [0.03, 0.04, 0.05, 0.03, 0.04],
            "bajo_malla": [0, 0, 1, 1, 0],
        }
    )
    return tabla


def test_rf2_excluye_las_plantas_con_kvpi_vacio():
    tabla, _ = excluir_sin_kvpi(_tabla_con_dos_vacios())

    assert list(tabla["id"]) == [1, 3, 5]
    assert tabla["KVPI_mean"].notna().all()


def test_rf2_la_advertencia_tiene_codigo_estable_y_la_cantidad():
    _, advertencias = excluir_sin_kvpi(_tabla_con_dos_vacios())

    assert len(advertencias) == 1
    assert advertencias[0].codigo == "PLANTAS_EXCLUIDAS"
    assert "2" in advertencias[0].mensaje


def test_rf2_sin_vacios_no_excluye_ni_advierte():
    entrada = _tabla_valida()

    tabla, advertencias = excluir_sin_kvpi(entrada)

    assert advertencias == []
    pd.testing.assert_frame_equal(tabla, entrada)


def test_rf2_no_modifica_la_tabla_de_entrada():
    entrada = _tabla_con_dos_vacios()
    copia = entrada.copy()

    excluir_sin_kvpi(entrada)

    pd.testing.assert_frame_equal(entrada, copia)
    assert len(entrada) == 5


def test_rf2_la_tabla_devuelta_es_independiente_de_la_entrada():
    entrada = _tabla_valida()

    tabla, _ = excluir_sin_kvpi(entrada)
    tabla.loc[0, "KVPI_mean"] = 99.0

    assert entrada.loc[0, "KVPI_mean"] == 0.50
