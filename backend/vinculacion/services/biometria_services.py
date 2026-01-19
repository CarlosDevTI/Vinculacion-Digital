# vinculacion/services/biometria_service.py

"""
SERVICIO DE INTEGRACIÓN CON PROVEEDOR DE BIOMETRÍA
==================================================
Maneja toda la comunicación con la API del proveedor
para consultar el estado de validación de identidad.
"""

import logging
import time

import requests
from django.conf import settings

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


class BiometriaService:
    """
    Servicio para interactuar con la API de validación biométrica.
    
    Este servicio encapsula toda la lógica de comunicación con el
    proveedor externo, haciendo que el resto del código no necesite
    conocer los detalles de la integración.
    """
    
    def __init__(self):
        """
        Constructor del servicio.
        
        Inicializa las credenciales y URLs desde settings.py
        """
        self.api_url = getattr(
            settings,
            'DECRIM_API_URL',
            'https://consultorid.com/api/digital/crear/registro.php'
        )
        self.username = getattr(settings, 'DECRIM_USERNAME', '')
        self.password = getattr(settings, 'DECRIM_PASSWORD', '')
        self.consulta_url = getattr(
            settings,
            'DECRIM_CONSULTA_URL',
            'https://consultorid.com/api/validacion/consultar/caso.php'
        )
        self.consulta_canal = getattr(settings, 'DECRIM_CONSULTA_CANAL', '0')
        self.consulta_certificado = getattr(settings, 'DECRIM_CONSULTA_CERTIFICADO', '0')
        
        # Timeout para las peticiones (segundos)
        self.timeout = 30
    
    def consultar_caso_por_dni(
        self,
        numero_cedula,
        idcaso=None,
        incluir_imagenes=False,
        incluir_certificado=None
    ):
        """
        Consulta el estado de validacion de un caso por numero de DNI o Idcaso.
        """
        certificado_valor = self.consulta_certificado if incluir_certificado is None else (
            "1" if incluir_certificado else "0"
        )
        if idcaso:
            idcaso_value = str(idcaso)
            dni_value = "0"
        else:
            idcaso_value = "0"
            dni_value = str(numero_cedula or "0")
        payload = {
            "Username": self.username,
            "Password": self.password,
            "Idcaso": idcaso_value,
            "Dni": dni_value,
            "Canal": str(self.consulta_canal),
            "Imagenes": "1" if incluir_imagenes else "0",
            "Certificado": str(certificado_valor)
        }

        start_time = time.monotonic()
        try:
            response = requests.post(
                self.consulta_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=self.timeout
            )
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            data = response.json() if response.content else {}

            if response.status_code == 200 and data.get('status') == 200:
                data_payload = data.get('data', {})
                return {
                    'exitoso': True,
                    'estado': data_payload.get('Estado'),
                    'idcaso': data_payload.get('Idcaso'),
                    'justificacion': data_payload.get('Justificacion', ''),
                    'datos_completos': data,
                    'request_data': payload,
                    'tiempo_respuesta_ms': elapsed_ms
                }

            if response.status_code == 404 or data.get('status') == 404:
                logger.info("Caso no encontrado en DECRIM: %s", payload)
                return {
                    'exitoso': False,
                    'estado': 'NO_ENCONTRADO',
                    'error': data.get('message', 'Caso no encontrado'),
                    'datos_completos': data,
                    'request_data': payload,
                    'tiempo_respuesta_ms': elapsed_ms
                }

            if response.status_code == 409 or data.get('status') == 409:
                logger.info("Caso en proceso en DECRIM (409): %s", payload)
                return {
                    'exitoso': False,
                    'estado': 'EN_PROCESO',
                    'error': data.get('message', 'Caso aun no disponible'),
                    'datos_completos': data,
                    'request_data': payload,
                    'tiempo_respuesta_ms': elapsed_ms
                }

            if response.status_code == 403 or data.get('status') == 403:
                logger.warning("Caso no autorizado para entidad en DECRIM: %s", payload)
                return {
                    'exitoso': False,
                    'estado': 'NO_AUTORIZADO',
                    'error': data.get('message', 'Caso no pertenece a la entidad'),
                    'datos_completos': data,
                    'request_data': payload,
                    'tiempo_respuesta_ms': elapsed_ms
                }

            return {
                'exitoso': False,
                'error': data.get('message') if isinstance(data, dict) else None
                or f'Error del proveedor: {response.status_code}',
                'datos_completos': data,
                'request_data': payload,
                'tiempo_respuesta_ms': elapsed_ms
            }

        except requests.exceptions.Timeout:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return {
                'exitoso': False,
                'error': 'Timeout: El proveedor no respondio a tiempo',
                'request_data': payload,
                'tiempo_respuesta_ms': elapsed_ms
            }

        except requests.exceptions.ConnectionError:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return {
                'exitoso': False,
                'error': 'No se pudo conectar con el proveedor de validacion',
                'request_data': payload,
                'tiempo_respuesta_ms': elapsed_ms
            }

        except Exception as e:
            logger.exception(f"Error inesperado consultando caso en DECRIM: {str(e)}")
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return {
                'exitoso': False,
                'error': f'Error inesperado: {str(e)}',
                'request_data': payload,
                'tiempo_respuesta_ms': elapsed_ms
            }

    def interpretar_estado(self, estado_codigo):
        """
        Interpreta el código de estado retornado por el proveedor.
        
        Args:
            estado_codigo (str): Código de estado del proveedor
            
        Returns:
            tuple: (estado_normalizado, descripcion)
                estado_normalizado: 'APROBADO', 'RECHAZADO', 'EN_PROCESO'
        """
        # Según la documentación, Estado=5 es aprobado
        # Ajustar según la documentación real del proveedor
        
        estado_map = {
            '5': ('APROBADO', 'Validación biométrica exitosa'),
            '3': ('RECHAZADO', 'Devuelto'),
            '2': ('RECHAZADO', 'Validación rechazada'),
            '1': ('APROBADO', 'Validado'),
        }

        estado = estado_map.get(str(estado_codigo))
        if not estado:
            logger.warning("Estado biometria desconocido: %s", estado_codigo)
            return ('EN_PROCESO', 'Estado desconocido')
        return estado

    def crear_registro_decrim(self, numero_cedula, tipo_documento, nombres):
        """
        Crea un registro digital en DECRIM y retorna el código y la URL.
        """
        payload = {
            "Username": self.username,
            "Password": self.password,
            "Dni": numero_cedula,
            "TipoDni": str(tipo_documento),
            "Nombres": nombres
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=self.timeout
            )
            data = response.json() if response.content else {}

            if response.status_code == 200 and data.get('status') == 200:
                data_payload = data.get('data', {})
                return {
                    'exitoso': True,
                    'codigo': data_payload.get('Codigo'),
                    'url': data_payload.get('Url'),
                    'response_data': data,
                    'request_data': payload
                }

            message = data.get('message') if isinstance(data, dict) else None
            return {
                'exitoso': False,
                'error': message or f'Error del proveedor: {response.status_code}',
                'response_data': data,
                'request_data': payload
            }

        except requests.exceptions.Timeout:
            return {
                'exitoso': False,
                'error': 'Timeout: El proveedor no respondió a tiempo',
                'request_data': payload
            }

        except requests.exceptions.ConnectionError:
            return {
                'exitoso': False,
                'error': 'No se pudo conectar con el proveedor de validación',
                'request_data': payload
            }

        except Exception as e:
            logger.exception(f"Error inesperado creando registro en DECRIM: {str(e)}")
            return {
                'exitoso': False,
                'error': f'Error inesperado: {str(e)}',
                'request_data': payload
            }
