"""Línea de comandos `kiwitracking` (spec 003): define los comandos y devuelve el código de salida.

Es una capa fina: no calcula nada. `main` devuelve el código y no llama a `sys.exit`, para poder probarse
en el mismo proceso; `__main__.py` y el punto de entrada de `pyproject.toml` lo convierten en salida.
"""

import argparse
import sys

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
    subcomandos = parser.add_subparsers(dest="comando", metavar="{mapa,analizar}", parser_class=_Parser)
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
    analizar.add_argument("--estado-frio", help="Estado de frío escrito a mano: Deficiente, Adecuado u Óptimo.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Corre la línea de comandos y devuelve el código de salida (RF-19)."""
    parser = construir_parser()
    try:
        argumentos = parser.parse_args(argv)
    except SystemExit as salida:  # `--help` (0) y los errores de uso (2) terminan así en `argparse`
        return salida.code if isinstance(salida.code, int) else 0

    if argumentos.comando is None:
        parser.print_help(sys.stderr)
        return 2
    raise NotImplementedError(f"El comando {argumentos.comando} todavía no está implementado.")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
