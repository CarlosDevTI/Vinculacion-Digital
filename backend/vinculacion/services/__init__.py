# vinculacion/services/__init__.py

"""
SERVICES - Capa de Lógica de Negocio
====================================
Aquí colocamos toda la lógica que NO es específica de las vistas.

Ventajas de separar en services:
- Código más limpio y mantenible
- Fácil de testear (unit tests)
- Reutilizable desde diferentes lugares
- Separación de responsabilidades
"""

from .biometria_services import BiometriaService
from .linix_services import LinixService
from .vinculacion_agil_services import VinculacionAgilService, VinculacionAgilError

__all__ = [
    'BiometriaService',
    'LinixService',
    'VinculacionAgilService',
    'VinculacionAgilError',
]
