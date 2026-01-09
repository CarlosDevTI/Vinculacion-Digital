# vinculacion/services/biometria_service.py

"""
SERVICIO DE INTEGRACIÓN CON PROVEEDOR DE BIOMETRÍA
==================================================
Maneja toda la comunicación con la API del proveedor
para consultar el estado de validación de identidad.
"""

import requests
import logging
from django.conf import settings
from datetime import datetime

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
        
        # Timeout para las peticiones (segundos)
        self.timeout = 30
    
    def consultar_caso_por_dni(self, numero_cedula):
        """
        Consulta el estado de validacion de un caso por numero de DNI.
        """
        logger.info("Consulta biometria desactivada hasta habilitar callback de DECRIM.")
        return {
            'exitoso': False,
            'estado': 'NO_ENCONTRADO',
            'error': 'Validacion pendiente: espera la respuesta de DECRIM',
            'tiempo_respuesta_ms': 0
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
            '1': ('EN_PROCESO', 'Validación en proceso'),
            '2': ('RECHAZADO', 'Validación rechazada'),
            # Agregar más estados según documentación
        }
        
        return estado_map.get(
            str(estado_codigo), 
            ('EN_PROCESO', 'Estado desconocido')
        )

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
