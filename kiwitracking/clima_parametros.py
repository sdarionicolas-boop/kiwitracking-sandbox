"""Parámetros del cálculo de GDD y horas de frío, con sus valores por defecto y su validación (RF-9)."""

from dataclasses import dataclass
from numbers import Integral, Real

from kiwitracking.resultado import ErrorDeEntrada

VENTANAS_FRIO = ("invierno", "temporada")


def _es_entero(valor) -> bool:
    return isinstance(valor, Integral) and not isinstance(valor, bool)


def _es_real(valor) -> bool:
    return isinstance(valor, Real) and not isinstance(valor, bool)


@dataclass(frozen=True)
class ParametrosClima:
    """Todos los valores por defecto de la spec 002 viven acá. Un valor no permitido da ErrorDeEntrada."""

    ventana_frio: str = "invierno"
    tbase: float = 10
    umbral_frio: float = 7
    meses_frio: tuple = (5, 6, 7, 8)
    mes_inicio_temporada: int = 7
    cobertura_minima: float = 0.9
    max_hueco_dias: int | None = 7
    umbral_optimo: float = 950
    umbral_adecuado: float = 750
    rango_fisico: tuple = (-60, 60)
    campana: int | None = None
    formato_fecha: str | None = None

    def __post_init__(self):
        if self.ventana_frio not in VENTANAS_FRIO:
            raise ErrorDeEntrada(
                f"ventana_frio={self.ventana_frio!r} no es válido. Valores permitidos: {', '.join(VENTANAS_FRIO)}."
            )
        if not _es_real(self.cobertura_minima) or not 0 <= self.cobertura_minima <= 1:
            raise ErrorDeEntrada(
                f"cobertura_minima={self.cobertura_minima!r} no es válido: debe ser un número entre 0 y 1."
            )
        if self.max_hueco_dias is not None and (not _es_entero(self.max_hueco_dias) or self.max_hueco_dias < 0):
            raise ErrorDeEntrada(
                f"max_hueco_dias={self.max_hueco_dias!r} no es válido: debe ser un entero no negativo, o None para no limitar."
            )
        if not (_es_real(self.umbral_optimo) and _es_real(self.umbral_adecuado)) or self.umbral_optimo <= self.umbral_adecuado:
            raise ErrorDeEntrada(
                f"umbral_optimo={self.umbral_optimo!r} debe ser mayor que umbral_adecuado={self.umbral_adecuado!r}."
            )
        self._validar_rango_fisico()
        if not _es_entero(self.mes_inicio_temporada) or not 1 <= self.mes_inicio_temporada <= 12:
            raise ErrorDeEntrada(
                f"mes_inicio_temporada={self.mes_inicio_temporada!r} no es válido: debe ser un entero entre 1 y 12."
            )
        self._validar_meses_frio()
        if self.campana is not None and not _es_entero(self.campana):
            raise ErrorDeEntrada(f"campana={self.campana!r} no es válido: debe ser un año entero, o None.")
        if self.formato_fecha is not None and (not isinstance(self.formato_fecha, str) or not self.formato_fecha):
            raise ErrorDeEntrada(
                f"formato_fecha={self.formato_fecha!r} no es válido: debe ser un texto como '%d/%m/%Y', o None."
            )

    def _validar_rango_fisico(self):
        rango = self.rango_fisico
        valido = (
            isinstance(rango, (tuple, list))
            and len(rango) == 2
            and all(_es_real(valor) for valor in rango)
            and rango[0] < rango[1]
        )
        if not valido:
            raise ErrorDeEntrada(
                f"rango_fisico={rango!r} no es válido: deben ser dos números (mínimo, máximo) con el mínimo menor que el máximo."
            )
        object.__setattr__(self, "rango_fisico", tuple(rango))

    def _validar_meses_frio(self):
        meses = self.meses_frio
        if not isinstance(meses, (tuple, list)) or not meses or not all(_es_entero(m) and 1 <= m <= 12 for m in meses):
            raise ErrorDeEntrada(
                f"meses_frio={meses!r} no es válido: debe tener al menos un mes, todos enteros entre 1 y 12."
            )
        meses = tuple(int(m) for m in meses)
        object.__setattr__(self, "meses_frio", meses)

        ordenados = sorted(set(meses))
        continuos = ordenados == list(range(ordenados[0], ordenados[-1] + 1))
        if self.ventana_frio == "invierno" and not continuos:
            raise ErrorDeEntrada(
                f"meses_frio={meses!r} cruza el fin de año o tiene saltos: en modo 'invierno' esta versión solo admite "
                "ventanas continuas dentro de un año calendario (por ejemplo, 5, 6, 7, 8)."
            )
