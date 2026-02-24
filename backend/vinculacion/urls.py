# vinculacion/urls.py

"""
URLS - Configuración de rutas de la API
========================================
Define los endpoints disponibles y los asocia con sus views.
"""

from django.conf import settings
from django.urls import path
from .views import (
    IniciarPreRegistroView,
    EstadoBiometriaView,
    DecrimTokenView,
    DecrimWebhookView,
    LinkLinixView,
    VinculacionAgilView,
    VerificarLinixView,
    VerificarLinixPendientesView,
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

    # PASO 3.2: Vinculacion agil (trama -> API LINIX)
    path(
        'vinculacion-agil/',
        VinculacionAgilView.as_view(),
        name='vinculacion-agil'
    ),
    
    # PASO 4: Verificar creación en LINIX
    path(
        'preregistro/<int:pk>/verificar-linix/',
        VerificarLinixView.as_view(),
        name='preregistro-verificar-linix'
    ),

    # Verificacion periodica en LINIX (n8n)
    path(
        'linix/verificar-pendientes/',
        VerificarLinixPendientesView.as_view(),
        name='linix-verificar-pendientes'
    ),
    
    # Obtener detalles completos
    path(
        'preregistro/<int:pk>/',
        PreRegistroDetailView.as_view(),
        name='preregistro-detail'
    ),

    # Webhook DECRIM
    path(
        'decrim/token/',
        DecrimTokenView.as_view(),
        name='decrim-token'
    ),
    path(
        'decrim/webhook/',
        DecrimWebhookView.as_view(),
        name='decrim-webhook'
    ),
    
]

if settings.DEBUG:
    # Testing (solo en desarrollo)
    urlpatterns.append(
        path(
            'test/oracle/',
            TestOracleConnectionView.as_view(),
            name='test-oracle'
        )
    )
