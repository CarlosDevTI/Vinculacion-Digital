# vinculacion/admin.py

"""
ADMIN - Panel de Administración de Django
==========================================
Registra los modelos para que aparezcan en /admin/
"""

from django.contrib import admin
from .models import PreRegistro, LogIntegracion


@admin.register(PreRegistro)
class PreRegistroAdmin(admin.ModelAdmin):
    """
    Configuración del modelo PreRegistro en el admin.
    
    Permite:
    - Ver listado con filtros
    - Buscar por cédula o nombres
    - Ver detalles completos
    - Exportar datos (opcional)
    """
    
    # Columnas que se muestran en la lista
    list_display = [
        'id',
        'numero_cedula',
        'nombres_completos',
        'estado_biometria',
        'intentos_biometria',
        'vetado',
        'estado_vinculacion',
        'flujo_linix_creado',
        'created_at'
    ]
    
    # Filtros en la barra lateral
    list_filter = [
        'estado_biometria',
        'vetado',
        'estado_vinculacion',
        'flujo_linix_creado',
        'created_at'
    ]
    
    # Campos por los que se puede buscar
    search_fields = [
        'numero_cedula',
        'nombres_completos',
        'id_tercero_linix'
    ]
    
    # Campos de solo lectura (no editables)
    readonly_fields = [
        'created_at',
        'updated_at',
        'fecha_validacion_biometria',
        'fecha_inicio_linix',
        'fecha_completado'
    ]
    
    # Organizar campos en secciones
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'numero_cedula',
                'nombres_completos',
                'fecha_expedicion'
            )
        }),
        ('Validación Biométrica', {
            'fields': (
                'estado_biometria',
                'idcaso_biometria',
                'justificacion_biometria',
                'fecha_validacion_biometria'
            )
        }),
        ('Control de Intentos', {
            'fields': (
                'intentos_biometria',
                'vetado',
                'mensaje_error'
            )
        }),
        ('Integración LINIX', {
            'fields': (
                'estado_vinculacion',
                'fecha_inicio_linix',
                'id_tercero_linix',
                'flujo_linix_creado',
                'fecha_completado',
                'datos_oracle'
            )
        }),
        ('Auditoría', {
            'fields': (
                'ip_registro',
                'user_agent',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)  # Sección colapsable
        }),
    )
    
    # Ordenar por más recientes primero
    ordering = ['-created_at']
    
    # Número de registros por página
    list_per_page = 50


@admin.register(LogIntegracion)
class LogIntegracionAdmin(admin.ModelAdmin):
    """
    Configuración del modelo LogIntegracion en el admin.
    
    Útil para debugging y auditoría.
    """
    
    list_display = [
        'id',
        'preregistro',
        'accion',
        'exitoso',
        'tiempo_respuesta_ms',
        'created_at'
    ]
    
    list_filter = [
        'accion',
        'exitoso',
        'created_at'
    ]
    
    search_fields = [
        'preregistro__numero_cedula',
        'error_message'
    ]
    
    readonly_fields = [
        'preregistro',
        'accion',
        'exitoso',
        'request_data',
        'response_data',
        'error_message',
        'tiempo_respuesta_ms',
        'created_at'
    ]
    
    # Vista de solo lectura (no se puede editar ni crear desde admin)
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    ordering = ['-created_at']
    list_per_page = 100
