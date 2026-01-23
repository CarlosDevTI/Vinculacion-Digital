# vinculacion/models.py

"""
MODELOS SIMPLIFICADOS PARA VINCULACIÓN DIGITAL
==============================================
Solo almacenamos lo esencial para el flujo de 4 pasos.
La información completa queda en LINIX (Oracle).
"""

from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone


class PreRegistro(models.Model):
    """
    Modelo para almacenar el rastro del proceso de vinculación.
    
    Este modelo NO almacena toda la info del usuario (eso está en LINIX),
    solo lo necesario para:
    - Validar identidad (paso 1-2)
    - Hacer seguimiento del flujo (auditoría)
    - Confirmar que el registro en LINIX fue exitoso (paso 4)
    """
    
    # ============================================
    # ESTADOS DEL FLUJO
    # ============================================
    
    # Estados de validación biométrica
    BIOMETRIA_PENDIENTE = 'PENDIENTE'
    BIOMETRIA_EN_PROCESO = 'EN_PROCESO'
    BIOMETRIA_APROBADO = 'APROBADO'
    BIOMETRIA_RECHAZADO = 'RECHAZADO'
    
    ESTADO_BIOMETRIA_CHOICES = [
        (BIOMETRIA_PENDIENTE, 'Pendiente'),
        (BIOMETRIA_EN_PROCESO, 'En Proceso'),
        (BIOMETRIA_APROBADO, 'Aprobado'),
        (BIOMETRIA_RECHAZADO, 'Rechazado'),
    ]
    
    # Estados del proceso general
    ESTADO_INICIADO = 'INICIADO'
    ESTADO_BIOMETRIA_OK = 'BIOMETRIA_OK'
    ESTADO_EN_LINIX = 'EN_LINIX'
    ESTADO_COMPLETADO = 'COMPLETADO'
    ESTADO_ERROR = 'ERROR'
    
    ESTADO_VINCULACION_CHOICES = [
        (ESTADO_INICIADO, 'Iniciado'),
        (ESTADO_BIOMETRIA_OK, 'Biometría Aprobada'),
        (ESTADO_EN_LINIX, 'Completando en LINIX'),
        (ESTADO_COMPLETADO, 'Completado'),
        (ESTADO_ERROR, 'Error'),
    ]

    # Tipos de documento (DECRIM)
    TIPO_DOC_CC = 1
    TIPO_DOC_TI = 2
    TIPO_DOC_RC = 3
    TIPO_DOC_CE = 4
    TIPO_DOC_DIAN = 5
    TIPO_DOC_NIT = 6
    TIPO_DOC_PEP = 7
    TIPO_DOC_PAS = 8
    TIPO_DOC_VISA = 9

    TIPO_DOCUMENTO_CHOICES = [
        (TIPO_DOC_CC, 'Cédula de ciudadanía'),
        (TIPO_DOC_TI, 'Tarjeta de identidad'),
        (TIPO_DOC_RC, 'Registro civil'),
        (TIPO_DOC_CE, 'Cédula de extranjería'),
        (TIPO_DOC_DIAN, 'Documento definido por la DIAN'),
        (TIPO_DOC_NIT, 'NIT'),
        (TIPO_DOC_PEP, 'P.E.P.'),
        (TIPO_DOC_PAS, 'Pasaporte'),
        (TIPO_DOC_VISA, 'Visa'),
    ]
    
    # ============================================
    # DATOS BÁSICOS (PASO 1)
    # ============================================
    
    # Validador: solo números
    cedula_validator = RegexValidator(
        regex=r'^\d+$',
        message='La cédula debe contener solo números'
    )
    
    numero_cedula = models.CharField(
        max_length=20,
        unique=True,  # Una sola vinculación por cédula
        validators=[cedula_validator],
        db_index=True,  # Índice para búsquedas rápidas
        help_text="Número de documento de identidad"
    )
    
    nombres_completos = models.CharField(
        max_length=200,
        help_text="Nombres completos del usuario"
    )

    tipo_documento = models.IntegerField(
        blank=True,
        null=True,
        choices=TIPO_DOCUMENTO_CHOICES,
        help_text="Tipo de documento según catálogo DECRIM"
    )
    
    fecha_expedicion = models.DateField(
        help_text="Fecha de expedición del documento"
    )

    agencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Agencia seleccionada por el usuario para la vinculación"
    )
    
    # ============================================
    # VALIDACIÓN BIOMÉTRICA (PASO 2)
    # ============================================
    
    idcaso_biometria = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="ID del caso en el sistema del proveedor"
    )

    url_biometria = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL generada por DECRIM para continuar el proceso"
    )
    
    estado_biometria = models.CharField(
        max_length=20,
        choices=ESTADO_BIOMETRIA_CHOICES,
        default=BIOMETRIA_PENDIENTE,
        db_index=True,
        help_text="Estado actual de la validación biométrica"
    )
    
    justificacion_biometria = models.TextField(
        blank=True,
        null=True,
        help_text="Mensaje del proveedor (ej: 'E01. Cedula OK, confronta facial OK')"
    )
    
    fecha_validacion_biometria = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Cuándo se completó la validación biométrica"
    )

    intentos_biometria = models.PositiveSmallIntegerField(
        default=0,
        help_text="Intentos fallidos de validacion biometrica"
    )

    vetado = models.BooleanField(
        default=False,
        help_text="Bloquea nuevos intentos hasta apertura manual"
    )
    
    # ============================================
    # INTEGRACIÓN CON LINIX (PASO 3 y 4)
    # ============================================
    
    fecha_inicio_linix = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Cuándo el usuario fue redirigido a LINIX"
    )
    
    id_tercero_linix = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="ID del tercero generado en LINIX (tabla gr_tercero)"
    )
    
    flujo_linix_creado = models.BooleanField(
        default=False,
        help_text="True cuando Oracle confirma que el flujo se creó correctamente"
    )
    
    datos_oracle = models.JSONField(
        blank=True,
        null=True,
        help_text="Datos completos retornados por el procedimiento Oracle"
    )
    
    # ============================================
    # CONTROL DE FLUJO
    # ============================================
    
    estado_vinculacion = models.CharField(
        max_length=30,
        choices=ESTADO_VINCULACION_CHOICES,
        default=ESTADO_INICIADO,
        db_index=True,
        help_text="Estado general del proceso"
    )
    
    fecha_completado = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Cuándo se completó todo el proceso exitosamente"
    )
    
    mensaje_error = models.TextField(
        blank=True,
        null=True,
        help_text="Mensaje de error si algo falló en el proceso"
    )
    
    # ============================================
    # AUDITORÍA
    # ============================================
    
    ip_registro = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP desde donde se inició el proceso"
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="Navegador del usuario"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del registro"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Última actualización"
    )
    
    # ============================================
    # METADATOS
    # ============================================
    
    class Meta:
        db_table = 'vinculacion_preregistro'
        verbose_name = 'Pre-Registro'
        verbose_name_plural = 'Pre-Registros'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['numero_cedula']),
            models.Index(fields=['estado_vinculacion']),
            models.Index(fields=['estado_biometria']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.numero_cedula} - {self.nombres_completos} ({self.get_estado_vinculacion_display()})"
    
    # ============================================
    # MÉTODOS ÚTILES
    # ============================================
    
    def puede_continuar_a_linix(self):
        """
        Verifica si el usuario puede avanzar al paso 3 (LINIX).
        
        Returns:
            bool: True si la biometría fue aprobada
        """
        return self.estado_biometria == self.BIOMETRIA_APROBADO
    
    def marcar_inicio_linix(self):
        """
        Marca que el usuario fue redirigido a LINIX.
        """
        self.estado_vinculacion = self.ESTADO_EN_LINIX
        self.fecha_inicio_linix = timezone.now()
        self.save(update_fields=['estado_vinculacion', 'fecha_inicio_linix', 'updated_at'])
    
    def marcar_como_completado(self, id_tercero, datos_oracle=None):
        """
        Marca el proceso como completado exitosamente.
        
        Args:
            id_tercero (str): ID del tercero en LINIX
            datos_oracle (dict): Datos completos retornados por Oracle
        """
        self.flujo_linix_creado = True
        self.id_tercero_linix = id_tercero
        self.estado_vinculacion = self.ESTADO_COMPLETADO
        self.fecha_completado = timezone.now()
        
        if datos_oracle:
            self.datos_oracle = datos_oracle
        
        self.save(update_fields=[
            'flujo_linix_creado',
            'id_tercero_linix',
            'estado_vinculacion',
            'fecha_completado',
            'datos_oracle',
            'updated_at'
        ])
    
    def marcar_error(self, mensaje_error):
        """
        Marca el proceso como error.
        
        Args:
            mensaje_error (str): Descripción del error
        """
        self.estado_vinculacion = self.ESTADO_ERROR
        self.mensaje_error = mensaje_error
        self.save(update_fields=['estado_vinculacion', 'mensaje_error', 'updated_at'])


class LogIntegracion(models.Model):
    """
    Registro de todas las llamadas a APIs externas.
    
    Útil para:
    - Debugging (ver qué salió mal)
    - Auditoría (quién hizo qué y cuándo)
    - Métricas (tiempos de respuesta, tasa de éxito)
    """
    
    ACCION_CONSULTA_BIOMETRIA = 'CONSULTA_BIOMETRIA'
    ACCION_REGISTRO_DECRIM = 'REGISTRO_DECRIM'
    ACCION_VERIFICACION_ORACLE = 'VERIFICACION_ORACLE'
    ACCION_WEBHOOK_N8N = 'WEBHOOK_N8N'
    
    ACCION_CHOICES = [
        (ACCION_CONSULTA_BIOMETRIA, 'Consulta Estado Biometría'),
        (ACCION_REGISTRO_DECRIM, 'Registro en DECRIM'),
        (ACCION_VERIFICACION_ORACLE, 'Verificación en Oracle'),
        (ACCION_WEBHOOK_N8N, 'Webhook a n8n'),
    ]
    
    preregistro = models.ForeignKey(
        PreRegistro,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Pre-registro asociado"
    )
    
    accion = models.CharField(
        max_length=50,
        choices=ACCION_CHOICES,
        help_text="Tipo de operación"
    )
    
    exitoso = models.BooleanField(
        help_text="True si fue exitoso, False si hubo error"
    )
    
    request_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Datos enviados en la petición"
    )
    
    response_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Datos recibidos en la respuesta"
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Mensaje de error si falló"
    )
    
    tiempo_respuesta_ms = models.IntegerField(
        blank=True,
        null=True,
        help_text="Tiempo de respuesta en milisegundos"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Cuándo ocurrió"
    )
    
    class Meta:
        db_table = 'vinculacion_log_integracion'
        verbose_name = 'Log de Integración'
        verbose_name_plural = 'Logs de Integración'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['preregistro', 'created_at']),
            models.Index(fields=['accion']),
        ]
    
    def __str__(self):
        estado = "✓" if self.exitoso else "✗"
        return f"{estado} {self.get_accion_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
