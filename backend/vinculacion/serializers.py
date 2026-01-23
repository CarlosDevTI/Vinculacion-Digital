# vinculacion/serializers.py

"""
SERIALIZERS - Transformadores entre JSON ↔ Python
=================================================
Los serializers convierten:
- JSON del frontend → Objetos Python (deserialización)
- Objetos Python → JSON para el frontend (serialización)

Son como "traductores" entre tu API y la base de datos.
"""

from rest_framework import serializers
from .models import PreRegistro, LogIntegracion
from datetime import date


class PreRegistroCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para CREAR un pre-registro (Paso 1).
    
    Valida:
    - Que la cédula no exista previamente
    - Que la fecha de expedición no sea futura
    - Formato de los campos
    """
    
    class Meta:
        model = PreRegistro
        fields = [
            'numero_cedula',
            'nombres_completos',
            'fecha_expedicion',
            'agencia',
            'tipo_documento',
        ]

    fecha_expedicion = serializers.DateField(
        input_formats=['%Y-%m-%d']
    )
    
    def validate_numero_cedula(self, value):
        """
        Validación personalizada para la cédula.
        
        Verifica:
        - Que tenga al menos 6 dígitos
        - Que no exista un registro previo con esa cédula
        
        Args:
            value (str): Número de cédula ingresado
            
        Returns:
            str: El valor validado
            
        Raises:
            serializers.ValidationError: Si la validación falla
        """
        # Validar longitud mínima
        if len(value) < 6:
            raise serializers.ValidationError(
                "La cédula debe tener al menos 6 dígitos"
            )
        
        # Validar que no exista (solo si estamos creando, no actualizando)
        if self.instance is None:  # self.instance es None cuando es creación
            if PreRegistro.objects.filter(numero_cedula=value).exists():
                raise serializers.ValidationError(
                    "Ya existe un registro con esta cédula. "
                    "Si deseas continuar un proceso anterior, contacta soporte."
                )
        
        return value
    
    def validate_fecha_expedicion(self, value):
        """
        Valida que la fecha de expedición sea lógica.
        
        Args:
            value (date): Fecha ingresada
            
        Returns:
            date: La fecha validada
            
        Raises:
            serializers.ValidationError: Si la fecha no es válida
        """
        # No puede ser fecha futura
        if value > date.today():
            raise serializers.ValidationError(
                "La fecha de expedición no puede ser futura"
            )
        
        # No puede ser muy antigua (ej: más de 100 años)
        from datetime import timedelta
        hace_100_anos = date.today() - timedelta(days=365*100)
        if value < hace_100_anos:
            raise serializers.ValidationError(
                "La fecha de expedición parece incorrecta"
            )
        
        return value

    def validate_tipo_documento(self, value):
        """
        Valida que el tipo de documento esté dentro del catálogo permitido.
        """
        if value is None:
            raise serializers.ValidationError("El tipo de documento es obligatorio")
        tipos_validos = {choice[0] for choice in PreRegistro.TIPO_DOCUMENTO_CHOICES}
        if value not in tipos_validos:
            raise serializers.ValidationError("Tipo de documento no válido")
        return value
    
    def _apply_auditoria(self, validated_data):
        request = self.context.get('request')
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')

            validated_data['ip_registro'] = ip
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        return validated_data

    def create(self, validated_data):
        """
        Crea el pre-registro con datos adicionales de auditoría.
        
        Args:
            validated_data (dict): Datos validados
            
        Returns:
            PreRegistro: Instancia creada
        """
        validated_data = self._apply_auditoria(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Actualiza el pre-registro (reintentos controlados).
        """
        validated_data = self._apply_auditoria(validated_data)
        return super().update(instance, validated_data)


class PreRegistroDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para LEER un pre-registro completo.
    
    Incluye campos calculados adicionales para el frontend.
    """
    
    # Campos calculados (no están en la BD, se generan al serializar)
    puede_continuar_a_linix = serializers.SerializerMethodField()
    link_biometria = serializers.SerializerMethodField()
    link_linix = serializers.SerializerMethodField()
    
    # Mostrar las etiquetas legibles de los choices
    estado_biometria_display = serializers.CharField(
        source='get_estado_biometria_display',
        read_only=True
    )
    estado_vinculacion_display = serializers.CharField(
        source='get_estado_vinculacion_display',
        read_only=True
    )
    
    class Meta:
        model = PreRegistro
        fields = [
            'id',
            'numero_cedula',
            'nombres_completos',
            'tipo_documento',
            'fecha_expedicion',
            'estado_biometria',
            'estado_biometria_display',
            'justificacion_biometria',
            'fecha_validacion_biometria',
            'url_biometria',
            'estado_vinculacion',
            'estado_vinculacion_display',
            'id_tercero_linix',
            'flujo_linix_creado',
            'fecha_completado',
            'mensaje_error',
            'created_at',
            'updated_at',
            # Campos calculados
            'puede_continuar_a_linix',
            'link_biometria',
            'link_linix',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_puede_continuar_a_linix(self, obj):
        """
        Indica si el usuario puede avanzar al paso 3 (LINIX).
        
        Args:
            obj (PreRegistro): Instancia del modelo
            
        Returns:
            bool: True si puede continuar
        """
        return obj.puede_continuar_a_linix()
    
    def get_link_biometria(self, obj):
        """
        Retorna el link del proveedor de validación biométrica.
        
        Args:
            obj (PreRegistro): Instancia del modelo
            
        Returns:
            str: URL del proveedor
        """
        # TODO: Reemplazar con el link real del proveedor
        return obj.url_biometria or ""
    
    def get_link_linix(self, obj):
        """
        Retorna el link de LINIX para completar la vinculación.
        
        Args:
            obj (PreRegistro): Instancia del modelo
            
        Returns:
            str: URL completa de LINIX
        """
        # Link base de LINIX
        base_url = "https://consulta.congente.coop/lnxPublico.php"
        
        # Parámetros fijos
        params = (
            "?nit=CONGENTE"
            "&objeto=gr_tercero_AsistidoCreacion"
            "&servicio=Y"
            "&metodo=Asistido"
            "&N_ROL=CRM"
            "&c_loop=01"
            "&publico=Y"
        )
        
        return f"{base_url}{params}"


class EstadoBiometriaSerializer(serializers.Serializer):
    """
    Serializer para la respuesta del endpoint de estado de biometría.
    
    Este NO está vinculado a un modelo, es solo para estructurar la respuesta.
    """
    estado_biometria = serializers.CharField()
    puede_continuar = serializers.BooleanField()
    justificacion = serializers.CharField(allow_blank=True, allow_null=True)
    mensaje = serializers.CharField()


class VerificacionLinixSerializer(serializers.Serializer):
    """
    Serializer para la respuesta del endpoint de verificación en LINIX/Oracle.
    """
    completado = serializers.BooleanField()
    id_tercero = serializers.CharField(allow_blank=True, allow_null=True)
    mensaje = serializers.CharField()
    datos_oracle = serializers.JSONField(required=False)


class LogIntegracionSerializer(serializers.ModelSerializer):
    """
    Serializer para leer los logs de integración.
    Útil para debugging en el admin.
    """
    preregistro_cedula = serializers.CharField(
        source='preregistro.numero_cedula',
        read_only=True
    )
    accion_display = serializers.CharField(
        source='get_accion_display',
        read_only=True
    )
    
    class Meta:
        model = LogIntegracion
        fields = [
            'id',
            'preregistro_cedula',
            'accion',
            'accion_display',
            'exitoso',
            'request_data',
            'response_data',
            'error_message',
            'tiempo_respuesta_ms',
            'created_at',
        ]
        read_only_fields = '__all__'
