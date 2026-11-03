"""Línea de comandos `kiwitracking` (spec 003): define los comandos y devuelve el código de salida.

Es una capa fina: no calcula nada. `main` devuelve el código y no llama a `sys.exit`, para poder probarse
en el mismo proceso; `__main__.py` y el punto de entrada de `pyproject.toml` lo convierten en salida.
"""

import argparse
import sys
import traceback
import unicodedata

from kiwitracking.clima import formatear_porcentaje
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.flujo import ResultadoFlujo, SolicitudAnalisis, ejecutar_analisis, ejecutar_kvpi, ejecutar_mapa
from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.salida import escribir_plantas_kvpi, escribir_resultados
from kiwitracking.validacion import ESTADOS_FRIO, validar_parametros

PROGRAMA = "kiwitracking"


class _Parser(argparse.ArgumentParser):
    """`argparse` con el encabezado "uso:" en español y los errores de uso con código 2."""

    def format_usage(self) -> str:
        return super().format_usage().replace("usage: ", "uso: ", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage: ", "uso: ", 1)

    def error(self, message: str):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _opciones_comunes() -> argparse.ArgumentParser:
    comunes = _Parser(add_help=False)
    comunes.add_argument("--plantas", required=True, help="CSV de plantas con id, KVPI_mean, KVPI_std, X e Y.")
    comunes.add_argument("--malla", help="GeoJSON con la zona bajo malla (opcional si el CSV trae bajo_malla).")
    comunes.add_argument("--crs-plantas", help="Sistema de coordenadas de X e Y, por ejemplo EPSG:4326 (obligatorio con --malla).")
    comunes.add_argument("--depurar", action="store_true", help="Muestra la traza completa de un error inesperado.")
    return comunes


def construir_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=PROGRAMA,
        description="Corrección por malla, clasificación de ambientes y recomendaciones del lote.",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="Muestra esta ayuda y termina.")
    subcomandos = parser.add_subparsers(dest="comando", metavar="{mapa,analizar,kvpi}", parser_class=_Parser)
    comunes = _opciones_comunes()

    mapa = subcomandos.add_parser(
        "mapa", parents=[comunes], add_help=False, help="Genera el mapa de verificación y muestra la huella del lote."
    )
    mapa.add_argument("-h", "--help", action="help", help="Muestra esta ayuda y termina.")
    mapa.add_argument("--salida", help="Archivo HTML del mapa (por defecto, mapa.html).")
    mapa.add_argument("--sin-fondo-satelital", action="store_true", help="Dibuja el mapa sin las teselas satelitales.")
    mapa.add_argument("--sobrescribir", action="store_true", help="Permite reemplazar un archivo existente.")

    analizar = subcomandos.add_parser(
        "analizar", parents=[comunes], add_help=False, help="Corrige por malla, clasifica y recomienda."
    )
    analizar.add_argument("-h", "--help", action="help", help="Muestra esta ayuda y termina.")
    analizar.add_argument("--huella", help="Huella que mostró el comando mapa (obligatoria).")
    analizar.add_argument("--salida", help="Carpeta de resultados (por defecto, resultados).")
    analizar.add_argument("--sobrescribir", action="store_true", help="Permite reemplazar resultados existentes.")
    analizar.add_argument("--correccion", help="Modo de corrección: auto, forzar o desactivar.")
    analizar.add_argument("--prueba-t", help="Prueba t del factor de corrección: welch o student.")
    analizar.add_argument("--alfa", type=float, help="Nivel de significancia de la prueba t.")
    analizar.add_argument("--min-plantas-grupo", type=int, help="Plantas mínimas por grupo para corregir.")
    analizar.add_argument("--p-ambiente", type=float, nargs=2, metavar=("BAJO", "ALTO"), help="Percentiles de los ambientes.")
    analizar.add_argument("--p-estabilidad", type=float, help="Percentil de estabilidad para Mantener.")
    analizar.add_argument("--no-escalar-std", action="store_true", help="No escala el desvío con el factor de corrección.")
    analizar.add_argument("--clima", help="CSV de clima diario con date, Tmax y Tmin.")
    analizar.add_argument("--campana", type=int, help="Año de inicio de la campaña (con --clima).")
    analizar.add_argument("--ventana-frio", help="Ventana de frío: invierno o temporada (con --clima).")
    analizar.add_argument("--formato-fecha", help="Formato de las fechas del clima si no son AAAA-MM-DD (con --clima).")
    analizar.add_argument("--cobertura-minima", type=float, help="Cobertura mínima de un período completo (con --clima).")
    analizar.add_argument("--max-hueco-dias", help="Hueco máximo en días, o ninguno (con --clima).")
    analizar.add_argument(
        "--origenes-estimados",
        help="Etiquetas de la columna origen del clima que cuentan como días estimados, separadas por comas (con --clima).",
    )
    analizar.add_argument("--estado-frio", help="Estado de frío escrito a mano: Deficiente, Adecuado u Óptimo.")

    kvpi = subcomandos.add_parser(
        "kvpi", add_help=False, help="Agrega la serie de KVPI por planta y la une con el muestreo."
    )
    kvpi.add_argument("-h", "--help", action="help", help="Muestra esta ayuda y termina.")
    kvpi.add_argument("--serie", required=True, help="CSV de la serie: una fila por planta y campaña (id, campaña, KVPI).")
    kvpi.add_argument("--muestreo", required=True, help="CSV del muestreo con id, X e Y (una fila por planta).")
    kvpi.add_argument("--salida", help="CSV de resultados (por defecto, plantas_kvpi.csv).")
    kvpi.add_argument("--min-campanas", type=int, help="Campañas con dato mínimas para calcular el desvío (2 o más).")
    kvpi.add_argument("--campanas", help="Etiquetas de campaña esperadas, separadas por comas.")
    kvpi.add_argument(
        "--cobertura-minima-campana", type=float, help="Proporción mínima de plantas con dato por campaña (entre 0 y 1)."
    )
    kvpi.add_argument("--sobrescribir", action="store_true", help="Permite reemplazar el archivo de salida.")
    kvpi.add_argument("--depurar", action="store_true", help="Muestra la traza completa de un error inesperado.")
    return parser


# Opciones que solo tienen sentido con --clima: (atributo de `argparse`, nombre en la línea de comandos).
OPCIONES_DE_CLIMA = (
    ("campana", "--campana"),
    ("ventana_frio", "--ventana-frio"),
    ("formato_fecha", "--formato-fecha"),
    ("cobertura_minima", "--cobertura-minima"),
    ("max_hueco_dias", "--max-hueco-dias"),
    ("origenes_estimados", "--origenes-estimados"),
)


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)).casefold().strip()


def _estado_exacto(escrito: str) -> str:
    """El estado con su texto exacto (spec 001); uno que no coincide con ninguno da el error de valores permitidos."""
    for estado in ESTADOS_FRIO:
        if _sin_tildes(estado) == _sin_tildes(escrito):
            return estado
    validar_parametros(estado_frio_ultima_campana=escrito)
    return escrito  # no se llega: validar_parametros ya levantó el error


def _max_hueco_dias(valor: str) -> int | None:
    if valor.strip().casefold() == "ninguno":
        return None
    try:
        return int(valor)
    except ValueError:
        raise ErrorDeEntrada(f"--max-hueco-dias={valor!r} no es válido: usá un número entero de días o 'ninguno'.") from None


def _origenes_estimados(valor: str) -> list[str]:
    """Las etiquetas separadas por comas, sin espacios al inicio ni al final; una etiqueta vacía es un error."""
    etiquetas = [etiqueta.strip() for etiqueta in valor.split(",")]
    if "" in etiquetas:
        raise ErrorDeEntrada(
            f"--origenes-estimados={valor!r} no es válido: indicá etiquetas separadas por comas, sin valores vacíos "
            "(por ejemplo, interpolado,estimado)."
        )
    return etiquetas


def interpretar_analizar(argumentos: argparse.Namespace) -> SolicitudAnalisis:
    """Revisa la combinación de opciones de `analizar` y deja solo lo indicado (RF-8, RF-9, RF-11, RF-24).

    Todo se comprueba antes de leer ningún archivo.
    """
    huella = (argumentos.huella or "").strip()
    if not huella:
        raise ErrorDeEntrada(
            "Falta --huella: corré primero `kiwitracking mapa`, revisá el mapa y copiá la huella que muestra."
        )
    if argumentos.clima is not None and argumentos.estado_frio is not None:
        raise ErrorDeEntrada("--clima y --estado-frio son excluyentes: el estado de frío sale de uno o del otro.")
    if argumentos.clima is None:
        sobran = [opcion for atributo, opcion in OPCIONES_DE_CLIMA if getattr(argumentos, atributo) is not None]
        if sobran:
            raise ErrorDeEntrada(f"{' y '.join(sobran)} solo se usa(n) con --clima.")

    parametros_analisis = {}
    for atributo in ("correccion", "prueba_t", "alfa", "min_plantas_grupo", "p_estabilidad"):
        if getattr(argumentos, atributo) is not None:
            parametros_analisis[atributo] = getattr(argumentos, atributo)
    if argumentos.p_ambiente is not None:
        parametros_analisis["p_ambiente"] = tuple(argumentos.p_ambiente)
    if argumentos.no_escalar_std:
        parametros_analisis["escalar_std"] = False
    validar_parametros(**{k: v for k, v in parametros_analisis.items() if k in ("correccion", "prueba_t")})

    parametros_clima = {}
    for atributo in ("ventana_frio", "formato_fecha", "cobertura_minima"):
        if getattr(argumentos, atributo) is not None:
            parametros_clima[atributo] = getattr(argumentos, atributo)
    if argumentos.max_hueco_dias is not None:
        parametros_clima["max_hueco_dias"] = _max_hueco_dias(argumentos.max_hueco_dias)
    if argumentos.origenes_estimados is not None:
        parametros_clima["origenes_estimados"] = _origenes_estimados(argumentos.origenes_estimados)
    if argumentos.clima is not None:
        ParametrosClima(**parametros_clima, campana=argumentos.campana)  # valida antes de leer el clima

    estado = _estado_exacto(argumentos.estado_frio) if argumentos.estado_frio is not None else None
    return SolicitudAnalisis(huella, argumentos.clima, estado, argumentos.campana, parametros_analisis, parametros_clima)


def _salida_sin_fallos_de_codificacion() -> None:
    """Que mostrar una tilde en una consola que no la admite no haga fallar el programa (RF-22)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # un flujo que no se puede reconfigurar se deja como está
            pass


def main(argv: list[str] | None = None) -> int:
    """Corre la línea de comandos y devuelve el código de salida (RF-19).

    0: se completó. 1: error de entrada. 2: uso incorrecto. 3: error inesperado (un fallo del programa).
    """
    _salida_sin_fallos_de_codificacion()
    parser = construir_parser()
    try:
        argumentos = parser.parse_args(argv)
    except SystemExit as salida:  # `--help` (0) y los errores de uso (2) terminan así en `argparse`
        return salida.code if isinstance(salida.code, int) else 0

    if argumentos.comando is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return {"mapa": _comando_mapa, "analizar": _comando_analizar, "kvpi": _comando_kvpi}[argumentos.comando](argumentos)
    except ErrorDeEntrada as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # un fallo del programa y no de los datos: no se oculta
        print(f"Error inesperado: {type(error).__name__}: {error}", file=sys.stderr)
        print("Parece un fallo del programa, no de tus datos. Usá --depurar para ver el detalle.", file=sys.stderr)
        if argumentos.depurar:
            traceback.print_exc()
        return 3


def _comando_mapa(argumentos) -> int:
    resultado = ejecutar_mapa(
        argumentos.plantas,
        argumentos.malla,
        argumentos.crs_plantas,
        argumentos.salida or "mapa.html",
        sin_fondo_satelital=argumentos.sin_fondo_satelital,
        sobrescribir=argumentos.sobrescribir,
    )
    print(f"Mapa guardado en {resultado.ruta}")
    print(f"Plantas bajo malla: {resultado.n_bajo_malla}")
    print(f"Plantas fuera de malla: {resultado.n_fuera_de_malla}")
    print(f"Huella: {resultado.huella}")
    print("Revisá el mapa y, si la malla está donde corresponde, copiá la huella en: kiwitracking analizar --huella <huella>")
    for advertencia in resultado.advertencias:
        print(f"Advertencia {advertencia.codigo}: {advertencia.mensaje}")
    return 0


def _numero(valor: float, decimales: int) -> str:
    return f"{valor:.{decimales}f}".replace(".", ",")


def _linea_de_estado_de_frio(flujo: ResultadoFlujo) -> str:
    estado = flujo.estado_frio
    if estado.origen == "clima":
        detalle = (
            f"clima, período {estado.periodo}, {_numero(estado.horas, 1)} h, cobertura {formatear_porcentaje(estado.cobertura)}"
        )
        return f"Estado de frío: {estado.estado} ({detalle})"
    if estado.origen == "manual":
        return f"Estado de frío: {estado.estado} (indicado a mano)"
    return "Estado de frío: ninguno (no se aplicó el ajuste por frío)"


def _comando_analizar(argumentos) -> int:
    solicitud = interpretar_analizar(argumentos)
    flujo = ejecutar_analisis(argumentos.plantas, argumentos.malla, argumentos.crs_plantas, solicitud)
    destino = argumentos.salida or "resultados"
    escribir_resultados(destino, flujo, sobrescribir=argumentos.sobrescribir)

    resumen = flujo.resultado.resumen
    print(f"Plantas analizadas: {len(flujo.resultado.tabla)}")
    factor = "sin calcular" if resumen.fc is None else _numero(resumen.fc, 4)
    print(f"Factor de corrección: {factor} (corrección aplicada: {'sí' if resumen.correccion_aplicada else 'no'})")
    print("Recomendaciones:")
    for recomendacion, cantidad in flujo.resultado.tabla["recomendacion"].value_counts().sort_index().items():
        print(f"  {recomendacion}: {cantidad}")
    print(_linea_de_estado_de_frio(flujo))
    for advertencia in flujo.advertencias:
        print(f"Advertencia {advertencia.codigo}: {advertencia.mensaje}")
    print(f"Resultados guardados en {destino}")
    return 0


def _cantidad(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _comando_kvpi(argumentos) -> int:
    """Solo se pasan al flujo los parámetros indicados: los valores por defecto son los de `ejecutar_kvpi`."""
    indicados = {}
    if argumentos.min_campanas is not None:
        indicados["min_campanas"] = argumentos.min_campanas
    if argumentos.campanas is not None:
        indicados["campanas"] = [etiqueta.strip() for etiqueta in argumentos.campanas.split(",")]
    if argumentos.cobertura_minima_campana is not None:
        indicados["cobertura_minima_campana"] = argumentos.cobertura_minima_campana
    resultado = ejecutar_kvpi(argumentos.serie, argumentos.muestreo, **indicados)
    destino = argumentos.salida or "plantas_kvpi.csv"
    escribir_plantas_kvpi(destino, resultado.tabla, sobrescribir=argumentos.sobrescribir)

    print(f"Plantas en el resultado: {len(resultado.tabla)}")
    print(f"Campañas encontradas (cobertura sobre las {_cantidad(resultado.n_plantas_muestreo, 'planta', 'plantas')} del muestreo):")
    for c in resultado.cobertura:
        print(f"  {c.campana}: {_cantidad(c.plantas_con_dato, 'planta', 'plantas')} con dato ({formatear_porcentaje(c.proporcion)})")
    print("Plantas según las campañas con dato:")
    for campanas, plantas in resultado.tabla["n_campanas"].value_counts().sort_index(ascending=False).items():
        print(f"  {_cantidad(int(campanas), 'campaña', 'campañas')}: {_cantidad(int(plantas), 'planta', 'plantas')}")
    for advertencia in resultado.advertencias:
        print(f"Advertencia {advertencia.codigo}: {advertencia.mensaje}")
    print(f"Resultado guardado en {destino}")
    print("Ese archivo es la entrada --plantas de `kiwitracking mapa` y `kiwitracking analizar`.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
