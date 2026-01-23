# vinculacion/views.py

"""
VIEWS - Endpoints de la API REST
=================================
Aquí definimos los endpoints que consumirá el frontend React.

Arquitectura:
- Usamos Django REST Framework (DRF)
- APIView para endpoints personalizados
- Validación con serializers
- Respuestas estandarizadas con Response
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
import base64
import hashlib
import hmac
import json
import time
import logging

from .models import PreRegistro, LogIntegracion
from .serializers import (
    PreRegistroCreateSerializer,
    PreRegistroDetailSerializer,
    EstadoBiometriaSerializer,
    VerificacionLinixSerializer
)
from .services import BiometriaService, LinixService

# Configurar logger
logger = logging.getLogger(__name__)


def _b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data):
    data_bytes = data.encode('ascii') if isinstance(data, str) else data
    padding = b'=' * (-len(data_bytes) % 4)
    return base64.urlsafe_b64decode(data_bytes + padding)


def _jwt_sign(payload, secret):
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(
        json.dumps(header, separators=(',', ':')).encode('utf-8')
    )
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(',', ':')).encode('utf-8')
    )
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def _jwt_verify(token, secret):
    try:
        header_b64, payload_b64, signature_b64 = token.split('.')
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            signing_input,
            hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), signature_b64):
            return None
        payload_raw = _b64url_decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_raw)
        exp = payload.get('exp')
        if exp and int(exp) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class IniciarPreRegistroView(APIView):
    """
    POST /api/v1/preregistro/iniciar/
    
    Crea un nuevo pre-registro (Paso 1).
    
    Request Body:
        {
            "numero_cedula": "123456789",
            "nombres_completos": "Carlos Daniel Ortiz Angel",
            "fecha_expedicion": "2010-05-20"
        }
    
    Response 201:
        {
            "id": 1,
            "numero_cedula": "123456789",
            "nombres_completos": "Carlos Daniel Ortiz Angel",
            "link_biometria": "https://proveedor.com/validacion",
            "estado_vinculacion": "INICIADO"
        }
    
    Response 400:
        {
            "error": "Ya existe un registro con esta cédula"
        }
    """
    
    permission_classes = [AllowAny]  # Endpoint público (sin autenticación)
    
    def post(self, request):
        """
        Maneja la petición POST para crear pre-registro.
        
        Args:
            request: Request de Django con los datos en request.data
            
        Returns:
            Response: JSON con los datos del pre-registro creado
        """
        
        logger.info("=== Iniciando pre-registro ===")
        
        numero_cedula_raw = request.data.get('numero_cedula')
        preregistro_existente = None
        if numero_cedula_raw:
            preregistro_existente = PreRegistro.objects.filter(
                numero_cedula=numero_cedula_raw
            ).first()

        max_intentos = int(getattr(settings, 'MAX_INTENTOS_BIOMETRIA', 2))
        if preregistro_existente and preregistro_existente.vetado:
            return Response(
                {
                    'error': 'Intentos de validacion agotados',
                    'detalle': (
                        'El ciudadano se encuentra vetado. Debe comunicarse con '
                        'Congente para habilitar un nuevo intento.'
                    ),
                    'codigo': 'VETADO',
                    'intentos': preregistro_existente.intentos_biometria,
                    'max_intentos': max_intentos
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Crear serializer con los datos recibidos
        # context={'request': request} permite que el serializer acceda al request
        serializer = PreRegistroCreateSerializer(
            instance=preregistro_existente,
            data=request.data,
            context={'request': request}
        )
        
        # Validar datos
        if serializer.is_valid():
            data = serializer.validated_data
            numero_cedula = data['numero_cedula']
            fecha_expedicion = data['fecha_expedicion']
            tipo_documento = data['tipo_documento']
            nombres = data['nombres_completos']

            if preregistro_existente:
                if preregistro_existente.estado_vinculacion == PreRegistro.ESTADO_COMPLETADO:
                    return Response(
                        {
                            'error': 'El ciudadano ya completo la vinculacion digital'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if preregistro_existente.url_biometria and preregistro_existente.estado_biometria in [
                    PreRegistro.BIOMETRIA_PENDIENTE,
                    PreRegistro.BIOMETRIA_EN_PROCESO,
                    PreRegistro.BIOMETRIA_APROBADO
                ]:
                    preregistro = serializer.save()
                    response_serializer = PreRegistroDetailSerializer(preregistro)
                    return Response(
                        response_serializer.data,
                        status=status.HTTP_200_OK
                    )

            # Validar si ya es asociado antes de generar registro digital
            linix_service = LinixService()
            fecha_expedicion_str = fecha_expedicion.strftime('%d/%m/%Y')
            resultado_actu = linix_service.consultar_actu(
                numero_cedula,
                fecha_expedicion_str
            )

            if not resultado_actu.get('exitoso'):
                return Response(
                    {
                        'error': 'No se pudo validar el estado del asociado',
                        'detalle': resultado_actu.get('error')
                    },
                    status=status.HTTP_502_BAD_GATEWAY
                )

            if resultado_actu.get('encontrado'):
                return Response(
                    {
                        'error': 'El ciudadano ya es asociado y no requiere vinculaci\u00f3n digital'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Guardar en base de datos
            preregistro = serializer.save()

            preregistro.estado_vinculacion = PreRegistro.ESTADO_INICIADO
            preregistro.mensaje_error = None
            preregistro.justificacion_biometria = None
            preregistro.fecha_validacion_biometria = None
            preregistro.estado_biometria = PreRegistro.BIOMETRIA_PENDIENTE
            preregistro.idcaso_biometria = None
            preregistro.url_biometria = None
            preregistro.save(update_fields=[
                'estado_vinculacion',
                'mensaje_error',
                'justificacion_biometria',
                'fecha_validacion_biometria',
                'estado_biometria',
                'idcaso_biometria',
                'url_biometria',
                'updated_at'
            ])

            # Crear registro en DECRIM para obtener URL de validación
            biometria_service = BiometriaService()
            resultado = biometria_service.crear_registro_decrim(
                numero_cedula,
                tipo_documento,
                nombres
            )

            LogIntegracion.objects.create(
                preregistro=preregistro,
                accion=LogIntegracion.ACCION_REGISTRO_DECRIM,
                exitoso=resultado.get('exitoso', False),
                request_data=resultado.get('request_data', {}),
                response_data=resultado.get('response_data', {}),
                error_message=resultado.get('error')
            )

            if not resultado.get('exitoso') or not resultado.get('url'):
                preregistro.marcar_error(
                    resultado.get('error', 'Error creando registro en DECRIM')
                )
                return Response(
                    {
                        'error': 'No se pudo generar el link de validación',
                        'detalle': resultado.get('error')
                    },
                    status=status.HTTP_502_BAD_GATEWAY
                )

            preregistro.idcaso_biometria = resultado.get('codigo')
            preregistro.url_biometria = resultado.get('url')
            preregistro.estado_biometria = PreRegistro.BIOMETRIA_EN_PROCESO
            preregistro.save(update_fields=[
                'idcaso_biometria',
                'url_biometria',
                'estado_biometria',
                'updated_at'
            ])
            
            logger.info(f"Pre-registro creado exitosamente: ID={preregistro.id}, Cédula={preregistro.numero_cedula}")
            
            # Serializar el objeto completo para la respuesta
            response_serializer = PreRegistroDetailSerializer(preregistro)
            
            # Retornar respuesta con código 201 (Created)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        else:
            # Si hay errores de validación
            logger.warning(f"Error de validación: {serializer.errors}")
            
            return Response(
                {
                    'error': 'Datos inválidos',
                    'detalles': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class EstadoBiometriaView(APIView):
    """
    GET /api/v1/preregistro/{id}/estado-biometria/
    
    Consulta el estado de la validación biométrica (Paso 2 - Polling).
    
    Este endpoint:
    1. Obtiene el pre-registro por ID
    2. Consulta la API del proveedor de biometría
    3. Actualiza el estado en la BD si cambió
    4. Retorna el estado actual
    
    Response 200:
        {
            "estado_biometria": "APROBADO",
            "puede_continuar": true,
            "justificacion": "E01. Cedula OK, confronta facial OK",
            "mensaje": "Validación biométrica exitosa"
        }
    
    Response 404:
        {
            "error": "Pre-registro no encontrado"
        }
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, pk):
        """
        Maneja la petición GET para consultar estado de biometría.
        
        Args:
            request: Request de Django
            pk (int): ID del pre-registro
            
        Returns:
            Response: JSON con el estado actual
        """
        
        logger.info(f"=== Consultando estado biometría para pre-registro ID={pk} ===")
        
        # Obtener el pre-registro o retornar 404 si no existe
        preregistro = get_object_or_404(PreRegistro, pk=pk)
        
        # Si ya está aprobado o rechazado, no consultar de nuevo
        if preregistro.estado_biometria in [
            PreRegistro.BIOMETRIA_APROBADO,
            PreRegistro.BIOMETRIA_RECHAZADO
        ]:
            logger.info(f"Estado ya finalizado: {preregistro.estado_biometria}")
            
            return Response({
                'estado_biometria': preregistro.estado_biometria,
                'puede_continuar': preregistro.puede_continuar_a_linix(),
                'justificacion': preregistro.justificacion_biometria,
                'mensaje': 'Estado ya determinado previamente'
            })
        
        # Consultar API del proveedor
        biometria_service = BiometriaService()
        resultado = biometria_service.consultar_caso_por_dni(
            preregistro.numero_cedula,
            preregistro.idcaso_biometria
        )
        
        # Crear log de la integración
        log = LogIntegracion.objects.create(
            preregistro=preregistro,
            accion=LogIntegracion.ACCION_CONSULTA_BIOMETRIA,
            exitoso=resultado.get('exitoso', False),
            request_data={'numero_cedula': preregistro.numero_cedula},
            response_data=resultado.get('datos_completos', {}),
            error_message=resultado.get('error'),
            tiempo_respuesta_ms=resultado.get('tiempo_respuesta_ms')
        )
        
        # Si la consulta fue exitosa
        if resultado['exitoso']:
            # Obtener estado del caso
            estado_codigo = resultado.get('estado', '')
            
            # Interpretar el estado
            estado_normalizado, descripcion = biometria_service.interpretar_estado(estado_codigo)
            
            # Actualizar pre-registro si el estado cambió
            if preregistro.estado_biometria != estado_normalizado:
                logger.info(f"Actualizando estado: {preregistro.estado_biometria} -> {estado_normalizado}")
                
                preregistro.estado_biometria = estado_normalizado
                preregistro.idcaso_biometria = resultado.get('idcaso')
                preregistro.justificacion_biometria = resultado.get('justificacion')
                
                # Si fue aprobado, actualizar fecha y estado de vinculación
                if estado_normalizado == PreRegistro.BIOMETRIA_APROBADO:
                    preregistro.fecha_validacion_biometria = timezone.now()
                    preregistro.estado_vinculacion = PreRegistro.ESTADO_BIOMETRIA_OK

                if estado_normalizado == PreRegistro.BIOMETRIA_RECHAZADO:
                    max_intentos = int(getattr(settings, 'MAX_INTENTOS_BIOMETRIA', 2))
                    preregistro.intentos_biometria = (preregistro.intentos_biometria or 0) + 1
                    preregistro.estado_vinculacion = PreRegistro.ESTADO_ERROR
                    preregistro.mensaje_error = 'Validacion de identidad rechazada.'
                    if preregistro.intentos_biometria >= max_intentos:
                        preregistro.vetado = True
                        preregistro.mensaje_error = (
                            'Validacion de identidad rechazada. '
                            'Debe comunicarse con Congente para habilitar un nuevo intento.'
                        )
                
                preregistro.save()
            
            # Preparar respuesta
            response_data = {
                'estado_biometria': estado_normalizado,
                'puede_continuar': preregistro.puede_continuar_a_linix(),
                'justificacion': resultado.get('justificacion', ''),
                'mensaje': descripcion
            }
            
            return Response(response_data)
        
        else:
            # Si hubo error consultando el proveedor
            error_msg = resultado.get('error', 'Error desconocido')
            
            # Si el caso no se encuentra, es normal (aún no ha validado)
            if resultado.get('estado') in ['NO_ENCONTRADO', 'EN_PROCESO']:
                logger.info(
                    "Consulta biometria sin resultado final (%s): %s",
                    resultado.get('estado'),
                    preregistro.numero_cedula
                )
                # Actualizar estado a EN_PROCESO si estaba PENDIENTE
                if preregistro.estado_biometria == PreRegistro.BIOMETRIA_PENDIENTE:
                    preregistro.estado_biometria = PreRegistro.BIOMETRIA_EN_PROCESO
                    preregistro.save()
                
                return Response({
                    'estado_biometria': PreRegistro.BIOMETRIA_EN_PROCESO,
                    'puede_continuar': False,
                    'justificacion': '',
                    'mensaje': 'Esperando validación biométrica. Por favor completa el proceso en la ventana del proveedor.'
                })

            if resultado.get('estado') == 'NO_AUTORIZADO':
                logger.warning(
                    "Consulta biometria no autorizada para entidad: %s",
                    preregistro.numero_cedula
                )
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_502_BAD_GATEWAY
                )

            
            # Cualquier otro error
            logger.error(f"Error consultando biometría: {error_msg}")
            
            return Response(
                {
                    'error': error_msg,
                    'estado_biometria': preregistro.estado_biometria
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DecrimTokenView(APIView):
    """
    POST /api/v1/decrim/token/

    Genera un token JWT para autenticar el webhook de DECRIM.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        user = request.data.get('user')
        password = request.data.get('password')

        expected_user = getattr(settings, 'DECRIM_WEBHOOK_USER', '')
        expected_password = getattr(settings, 'DECRIM_WEBHOOK_PASSWORD', '')
        secret = getattr(settings, 'DECRIM_WEBHOOK_JWT_SECRET', '')
        ttl = getattr(settings, 'DECRIM_WEBHOOK_TOKEN_TTL', 300)

        if not expected_user or not expected_password or not secret:
            return Response(
                {'error': 'Webhook credentials not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not user or not password:
            return Response(
                {'error': 'Missing credentials'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user != expected_user or password != expected_password:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        now = int(time.time())
        token = _jwt_sign(
            {
                'sub': user,
                'iat': now,
                'exp': now + int(ttl)
            },
            secret
        )

        return Response({'token': token})


class DecrimWebhookView(APIView):
    """
    POST /api/v1/decrim/webhook/

    Recibe resultados de validacion en tiempo real desde DECRIM.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        secret = getattr(settings, 'DECRIM_WEBHOOK_JWT_SECRET', '')
        if not secret:
            return Response(
                {'status': '500', 'message': 'Webhook secret not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        whitelist = getattr(settings, 'DECRIM_WEBHOOK_IP_WHITELIST', [])
        if whitelist:
            client_ip = _get_client_ip(request)
            if client_ip not in whitelist:
                logger.warning("Webhook rechazado por IP no permitida: %s", client_ip)
                return Response(
                    {'status': '403', 'message': 'Forbidden'},
                    status=status.HTTP_403_FORBIDDEN
                )

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response(
                {'status': '401', 'message': 'Unauthorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(' ', 1)[1].strip()
        if not _jwt_verify(token, secret):
            return Response(
                {'status': '401', 'message': 'Unauthorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data or {}
        idcaso = data.get('Idcaso')
        dni = data.get('Dni')
        estado = data.get('Estado')
        justificacion = data.get('Justificacion', '')

        if not idcaso and not dni:
            return Response(
                {'status': '400', 'message': 'Idcaso o Dni requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        preregistro = None
        if idcaso:
            preregistro = (
                PreRegistro.objects
                .filter(idcaso_biometria=str(idcaso))
                .order_by('-created_at')
                .first()
            )

        if not preregistro and dni:
            preregistro = (
                PreRegistro.objects
                .filter(numero_cedula=str(dni))
                .order_by('-created_at')
                .first()
            )

        if not preregistro:
            return Response(
                {
                    'status': '404',
                    'message': f'Caso ID {idcaso or dni} no encontrado.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        biometria_service = BiometriaService()
        estado_normalizado, descripcion = biometria_service.interpretar_estado(estado)
        preregistro.estado_biometria = estado_normalizado
        if idcaso:
            preregistro.idcaso_biometria = str(idcaso)
        if justificacion:
            preregistro.justificacion_biometria = justificacion

        if estado_normalizado == PreRegistro.BIOMETRIA_APROBADO:
            preregistro.fecha_validacion_biometria = timezone.now()
            preregistro.estado_vinculacion = PreRegistro.ESTADO_BIOMETRIA_OK

        preregistro.save()

        return Response(
            {
                'status': '200',
                'message': f'Caso ID {preregistro.idcaso_biometria} recibido y almacenado con exito.'
            }
        )


class LinkLinixView(APIView):
    """
    GET /api/v1/preregistro/{id}/link-linix/
    
    Genera el link de LINIX para que el usuario complete el formulario (Paso 3).
    
    Este endpoint:
    1. Verifica que la biometría esté aprobada
    2. Marca que el usuario está en proceso de LINIX
    3. Retorna el link completo
    
    Response 200:
        {
            "link_linix": "https://consulta.congente.coop/lnxPublico.php?...",
            "mensaje": "Redirigiendo a formulario de vinculación"
        }
    
    Response 400:
        {
            "error": "Debes completar la validación biométrica primero"
        }
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, pk):
        """
        Maneja la petición GET para obtener el link de LINIX.
        
        Args:
            request: Request de Django
            pk (int): ID del pre-registro
            
        Returns:
            Response: JSON con el link de LINIX
        """
        
        logger.info(f"=== Generando link LINIX para pre-registro ID={pk} ===")
        
        # Obtener pre-registro
        preregistro = get_object_or_404(PreRegistro, pk=pk)
        
        # Verificar que puede continuar
        if not preregistro.puede_continuar_a_linix():
            logger.warning(f"Intento de acceder a LINIX sin biometría aprobada: {preregistro.numero_cedula}")
            
            return Response(
                {
                    'error': 'Debes completar la validación biométrica exitosamente antes de continuar',
                    'estado_biometria': preregistro.estado_biometria
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Marcar que está iniciando proceso en LINIX
        preregistro.marcar_inicio_linix()
        
        # Generar link
        serializer = PreRegistroDetailSerializer(preregistro)
        link_linix = serializer.data['link_linix']
        
        logger.info(f"Link generado exitosamente para cédula: {preregistro.numero_cedula}")
        
        return Response({
            'link_linix': link_linix,
            'mensaje': 'Por favor completa el formulario de vinculación en LINIX. Una vez termines, regresa a esta página.'
        })


class VerificarLinixView(APIView):
    """
    POST /api/v1/preregistro/{id}/verificar-linix/
    
    Verifica que el flujo se haya creado exitosamente en LINIX/Oracle (Paso 4).
    
    Este endpoint:
    1. Ejecuta procedimiento almacenado en Oracle
    2. Verifica que el tercero exista y el flujo esté creado
    3. Actualiza el estado del pre-registro
    4. Opcionalmente dispara webhook a n8n
    
    Response 200:
        {
            "completado": true,
            "id_tercero": "12345",
            "mensaje": "¡Vinculación completada exitosamente!",
            "datos_oracle": {...}
        }
    
    Response 404:
        {
            "completado": false,
            "mensaje": "No se encontró el registro en LINIX. Por favor completa el formulario."
        }
    
    Response 500:
        {
            "error": "Error consultando Oracle"
        }
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request, pk):
        """
        Maneja la petición POST para verificar creación en LINIX.
        
        Args:
            request: Request de Django
            pk (int): ID del pre-registro
            
        Returns:
            Response: JSON con el resultado de la verificación
        """
        
        logger.info(f"=== Verificando creación en LINIX para pre-registro ID={pk} ===")
        
        # Obtener pre-registro
        preregistro = get_object_or_404(PreRegistro, pk=pk)
        
        # Verificar que esté en estado correcto
        if preregistro.estado_vinculacion not in [
            PreRegistro.ESTADO_EN_LINIX,
            PreRegistro.ESTADO_BIOMETRIA_OK
        ]:
            logger.warning(f"Intento de verificar en estado inválido: {preregistro.estado_vinculacion}")
            
            return Response(
                {
                    'error': 'El estado actual no permite verificación',
                    'estado_actual': preregistro.estado_vinculacion
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ejecutar verificación en Oracle
        linix_service = LinixService()
        resultado = linix_service.verificar_flujo_vinculacion(preregistro.numero_cedula)
        
        # Crear log de la integración
        log = LogIntegracion.objects.create(
            preregistro=preregistro,
            accion=LogIntegracion.ACCION_VERIFICACION_ORACLE,
            exitoso=resultado.get('exitoso', False),
            request_data={'numero_cedula': preregistro.numero_cedula},
            response_data=resultado.get('datos_completos', {}),
            error_message=resultado.get('error')
        )
        
        # Si la consulta a Oracle fue exitosa
        if resultado['exitoso']:
            
            # Si se encontró el tercero
            if resultado['encontrado']:
                id_tercero = resultado['id_tercero']
                
                logger.info(f"Flujo verificado exitosamente: ID_TERCERO={id_tercero}")
                
                # Marcar como completado
                preregistro.marcar_como_completado(
                    id_tercero=id_tercero,
                    datos_oracle=resultado.get('datos_completos')
                )
                
                # Disparar webhook a n8n para notificaciones
                self._enviar_webhook_n8n(preregistro)
                
                return Response({
                    'completado': True,
                    'id_tercero': id_tercero,
                    'mensaje': '¡Vinculación completada exitosamente! Un asesor se contactará contigo pronto.',
                    'datos_oracle': resultado.get('datos_completos')
                })
            
            else:
                # No se encontró el registro en LINIX
                logger.warning(f"No se encontró tercero en LINIX para cédula: {preregistro.numero_cedula}")
                
                return Response({
                    'completado': False,
                    'mensaje': 'No se encontró tu registro en LINIX. Por favor verifica que hayas completado el formulario correctamente.',
                    'sugerencia': 'Si completaste el formulario hace menos de 5 minutos, espera un momento e intenta nuevamente.'
                }, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # Error ejecutando el procedimiento
            error_msg = resultado.get('error', 'Error desconocido')
            logger.error(f"Error verificando LINIX: {error_msg}")
            
            return Response(
                {
                    'error': 'Error al verificar el registro',
                    'detalle': error_msg
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _enviar_webhook_n8n(self, preregistro):
        """
        Método privado para disparar webhook a n8n.
        
        Args:
            preregistro (PreRegistro): Instancia del pre-registro
        """
        import requests
        
        # La URL del webhook debe estar en settings.py
        webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', None)
        
        if not webhook_url:
            logger.warning("N8N_WEBHOOK_URL no está configurada. No se enviará el webhook.")
            return
        
        try:
            payload = {
                'id_preregistro': preregistro.id,
                'numero_cedula': preregistro.numero_cedula,
                'nombres_completos': preregistro.nombres_completos,
                'agencia': preregistro.agencia,
                'id_tercero_linix': preregistro.id_tercero_linix,
                'fecha_completado': preregistro.fecha_completado.isoformat() if preregistro.fecha_completado else None
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            # Crear log del webhook
            LogIntegracion.objects.create(
                preregistro=preregistro,
                accion=LogIntegracion.ACCION_WEBHOOK_N8N,
                exitoso=200 <= response.status_code < 300,
                request_data=payload,
                response_data=response.json() if 200 <= response.status_code < 300 and response.content else None,
                error_message=response.text if not (200 <= response.status_code < 300) else None
            )
            
            logger.info(f"Webhook n8n enviado: Status={response.status_code}")
        
        except Exception as e:
            logger.error(f"Error enviando webhook n8n: {str(e)}")
            LogIntegracion.objects.create(
                preregistro=preregistro,
                accion=LogIntegracion.ACCION_WEBHOOK_N8N,
                exitoso=False,
                error_message=str(e)
            )


class VerificarLinixPendientesView(APIView):
    """
    POST /api/v1/linix/verificar-pendientes/

    Ejecuta verificacion en Oracle para preregistros pendientes
    y retorna los que quedaron completados.

    Body (opcional):
        {
            "limit": 100,
            "ids": [1, 2, 3]
        }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        limit = request.data.get('limit')
        ids = request.data.get('ids')

        try:
            limit = int(limit) if limit is not None else None
        except (TypeError, ValueError):
            limit = None

        preregistros = PreRegistro.objects.filter(
            flujo_linix_creado=False,
            estado_biometria=PreRegistro.BIOMETRIA_APROBADO,
            estado_vinculacion__in=[
                PreRegistro.ESTADO_EN_LINIX,
                PreRegistro.ESTADO_BIOMETRIA_OK
            ]
        ).order_by('created_at')

        if ids:
            preregistros = preregistros.filter(id__in=ids)

        if limit:
            preregistros = preregistros[:limit]

        linix_service = LinixService()
        completados = []
        errores = []
        procesados = 0

        for preregistro in preregistros:
            procesados += 1
            resultado = linix_service.verificar_flujo_vinculacion(preregistro.numero_cedula)

            LogIntegracion.objects.create(
                preregistro=preregistro,
                accion=LogIntegracion.ACCION_VERIFICACION_ORACLE,
                exitoso=resultado.get('exitoso', False),
                request_data={
                    'numero_cedula': preregistro.numero_cedula,
                    'origen': 'n8n'
                },
                response_data=resultado.get('datos_completos', {}),
                error_message=resultado.get('error')
            )

            if resultado.get('exitoso') and resultado.get('encontrado'):
                preregistro.marcar_como_completado(
                    id_tercero=resultado.get('id_tercero'),
                    datos_oracle=resultado.get('datos_completos')
                )
                completados.append({
                    'id': preregistro.id,
                    'numero_cedula': preregistro.numero_cedula,
                    'nombres_completos': preregistro.nombres_completos,
                    'agencia': preregistro.agencia,
                    'id_tercero_linix': preregistro.id_tercero_linix,
                    'fecha_completado': (
                        preregistro.fecha_completado.isoformat()
                        if preregistro.fecha_completado
                        else None
                    )
                })
            elif not resultado.get('exitoso'):
                errores.append({
                    'id': preregistro.id,
                    'numero_cedula': preregistro.numero_cedula,
                    'error': resultado.get('error')
                })

        return Response(
            {
                'processed': procesados,
                'completed': completados,
                'errors': errores
            }
        )


class PreRegistroDetailView(APIView):
    """
    GET /api/v1/preregistro/{id}/
    
    Obtiene los detalles completos de un pre-registro.
    
    Útil para:
    - Debugging
    - Dashboard de administración
    - Recuperar estado después de refrescar página
    
    Response 200:
        {
            "id": 1,
            "numero_cedula": "123456789",
            "nombres_completos": "...",
            "estado_biometria": "APROBADO",
            "estado_vinculacion": "COMPLETADO",
            ...
        }
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, pk):
        """
        Maneja la petición GET para obtener detalles.
        
        Args:
            request: Request de Django
            pk (int): ID del pre-registro
            
        Returns:
            Response: JSON con todos los detalles
        """
        
        preregistro = get_object_or_404(PreRegistro, pk=pk)
        serializer = PreRegistroDetailSerializer(preregistro)
        
        return Response(serializer.data)


# ============================================
# VIEW PARA TESTING (Desarrollo)
# ============================================

class TestOracleConnectionView(APIView):
    """
    GET /api/v1/test/oracle/
    
    Endpoint de utilidad para probar la conexión con Oracle.
    
    ⚠️ IMPORTANTE: Eliminar o proteger en producción
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Prueba la conexión con Oracle.
        
        Returns:
            Response: Estado de la conexión
        """
        
        linix_service = LinixService()
        
        if linix_service.test_connection():
            return Response({
                'status': 'success',
                'mensaje': 'Conexión con Oracle exitosa'
            })
        else:
            return Response(
                {
                    'status': 'error',
                    'mensaje': 'No se pudo conectar con Oracle'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
