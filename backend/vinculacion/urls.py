# vinculacion/urls.py

"""
URLS - Configuración de rutas de la API
========================================
Define los endpoints disponibles y los asocia con sus views.
"""

from django.urls import path
from .views import (
    IniciarPreRegistroView,
    EstadoBiometriaView,
    LinkLinixView,
    VerificarLinixView,
    PreRegistroDetailView,
    TestOracleConnectionView
)

# Namespace de la app (útil para reverse())
app_name = 'vinculacion'

urlpatterns = [
    # PASO 1: Iniciar pre-registro
    path(
        'preregistro/iniciar/',
        IniciarPreRegistroView.as_view(),
        name='preregistro-iniciar'
    ),
    
    # PASO 2: Consultar estado de biometría (polling)
    path(
        'preregistro/<int:pk>/estado-biometria/',
        EstadoBiometriaView.as_view(),
        name='preregistro-estado-biometria'
    ),
    
    # PASO 3: Obtener link de LINIX
    path(
        'preregistro/<int:pk>/link-linix/',
        LinkLinixView.as_view(),
        name='preregistro-link-linix'
    ),
    
    # PASO 4: Verificar creación en LINIX
    path(
        'preregistro/<int:pk>/verificar-linix/',
        VerificarLinixView.as_view(),
        name='preregistro-verificar-linix'
    ),
    
    # Obtener detalles completos
    path(
        'preregistro/<int:pk>/',
        PreRegistroDetailView.as_view(),
        name='preregistro-detail'
    ),
    
    # Testing (remover en producción)
    path(
        'test/oracle/',
        TestOracleConnectionView.as_view(),
        name='test-oracle'
    ),
]