"""Elección del estado de frío de la campaña, para alimentar `analizar()` de la spec 001 (spec 002)."""

from dataclasses import dataclass, field
from numbers import Integral

from kiwitracking.clima import ResultadoClima, formatear_porcentaje
from kiwitracking.resultado import Advertencia, ErrorDeEntrada


@dataclass
class EstadoCampana:
    """El estado de frío elegido (utilizable como `estado_frio_ultima_campana`) y de qué período salió.

    Si ningún período es clasificable, todo queda vacío salvo las advertencias. `dias_estimados` y
    `proporcion_estimada` son el recuento del período elegido (spec 005); quedan vacíos si el clima no
    trae `origen` o si no hay período elegido.
    """

    estado: str | None
    periodo: int | None
    horas: float | None
    cobertura: float | None
    hueco_maximo: int | None
    advertencias: list[Advertencia] = field(default_factory=list)
    dias_estimados: int | None = None
    proporcion_estimada: float | None = None


def estado_frio_de_campana(resultado: ResultadoClima, campana: int | None = None) -> EstadoCampana:
    """El estado de frío de una campaña (RF-22 a RF-25, RF-28).

    Con `campana=Y` se usa el período de etiqueta Y: en modo "invierno", el invierno de ese año, que
    precede a la campaña Y/Y+1; en modo "temporada", la temporada Y. Si ese período no existe o no es
    clasificable, es un error: no se reemplaza por otro. Sin `campana`, se usa la ventana clasificable
    más reciente (una más nueva pero truncada se salta) y se avisa que puede ser posterior a la última
    campaña analizada. Sin ninguna clasificable, el estado queda vacío y se avisa.
    """
    if campana is not None and (not isinstance(campana, Integral) or isinstance(campana, bool)):
        raise ErrorDeEntrada(f"campana={campana!r} no es válido: debe ser un año entero, o None.")

    if campana is not None:
        fila = _fila_de_la_campana(resultado, int(campana))
        avisos = []
    else:
        clasificables = resultado.frio[resultado.frio["estado_frio"].notna()]
        if clasificables.empty:
            aviso = Advertencia(
                "SIN_PERIODO_CLASIFICABLE",
                "Ninguna ventana de frío es clasificable (cobertura o huecos insuficientes): no hay estado de frío "
                "para la última campaña.",
            )
            return EstadoCampana(None, None, None, None, None, [aviso])
        fila = clasificables.loc[clasificables["periodo"].idxmax()]
        avisos = [
            Advertencia(
                "CAMPANA_NO_INDICADA",
                f"No se indicó la campaña: se usó el período {int(fila['periodo'])} ({fila['estado_frio']}, "
                f"{float(fila['Horas_Frio']):.0f} h), el más reciente clasificable; puede ser posterior a la "
                "última campaña analizada.",
            )
        ]

    periodo, cobertura = int(fila["periodo"]), float(fila["cobertura"])
    if cobertura < 1:
        avisos.append(
            Advertencia(
                "COBERTURA_PARCIAL",
                f"Frío, ventana {periodo}: cobertura {formatear_porcentaje(cobertura)}; el estado está calculado "
                "con los días disponibles.",
            )
        )
    dias_estimados, proporcion_estimada = _recuento_del_periodo(resultado, periodo)
    if dias_estimados:
        avisos.append(
            Advertencia(
                "DIAS_ESTIMADOS",
                f"Frío, ventana {periodo}: {dias_estimados} de {int(fila['dias_disponibles'])} días "
                f"({formatear_porcentaje(proporcion_estimada)}) son estimados, no son mediciones; el estado de frío "
                "depende de ellos.",
            )
        )
    return EstadoCampana(
        str(fila["estado_frio"]),
        periodo,
        float(fila["Horas_Frio"]),
        cobertura,
        int(fila["hueco_maximo"]),
        avisos,
        dias_estimados,
        proporcion_estimada,
    )


def _recuento_del_periodo(resultado: ResultadoClima, periodo: int) -> tuple[int | None, float | None]:
    """Los días estimados del período y su proporción, o `(None, None)` si el clima no trae el recuento."""
    filas = resultado.estimados[resultado.estimados["periodo"] == periodo]
    if filas.empty:
        return None, None
    return int(filas["dias_estimados"].iloc[0]), float(filas["proporcion_estimada"].iloc[0])


def _fila_de_la_campana(resultado: ResultadoClima, campana: int):
    nombre = f"{'invierno' if resultado.ventana_frio == 'invierno' else 'temporada'} {campana}"
    filas = resultado.frio[resultado.frio["periodo"] == campana]
    if filas.empty:
        raise ErrorDeEntrada(f"No se puede usar la campaña {campana}: el {nombre} no tiene datos (sin datos).")
    fila = filas.iloc[0]
    if fila["estado_frio"] is None or fila["estado_frio"] != fila["estado_frio"]:
        raise ErrorDeEntrada(
            f"No se puede usar la campaña {campana}: el {nombre} no es clasificable "
            f"(cobertura {formatear_porcentaje(float(fila['cobertura']))}, hueco máximo {int(fila['hueco_maximo'])} días)."
        )
    return fila
