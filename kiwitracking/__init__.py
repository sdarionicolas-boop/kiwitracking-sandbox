"""KiwiTracking: núcleo de corrección por malla, ambientes y recomendaciones."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("kiwitracking")  # la única fuente de verdad es pyproject.toml
except PackageNotFoundError:  # el código se ejecutó sin instalar el paquete
    __version__ = "desconocida"
