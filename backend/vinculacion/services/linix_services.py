# vinculacion/services/linix_service.py

"""
SERVICIO DE INTEGRACIÓN CON ORACLE/LINIX
=========================================
Maneja la conexión con la base de datos Oracle
y la ejecución de procedimientos almacenados.
"""

import cx_Oracle
import logging
from django.conf import settings
from contextlib import contextmanager

# Configurar logger
logger = logging.getLogger(__name__)


class LinixService:
    """
    Servicio para interactuar con la base de datos Oracle de LINIX.
    
    Este servicio encapsula:
    - Conexión a Oracle
    - Ejecución de procedimientos almacenados
    - Manejo de errores de BD
    """
    
    def __init__(self):
        """
        Constructor del servicio.
        
        Inicializa los parámetros de conexión desde settings.py
        """
        self.oracle_user = getattr(settings, 'ORACLE_USER', '')
        self.oracle_password = getattr(settings, 'ORACLE_PASSWORD', '')
        self.oracle_dsn = getattr(settings, 'ORACLE_DSN', '')  # host:port/service_name
        
        # Configuración de encoding
        self.encoding = 'UTF-8'
    
    @contextmanager
    def get_connection(self):
        """
        Context manager para manejar conexiones a Oracle.
        
        Uso:
            with service.get_connection() as connection:
                cursor = connection.cursor()
                # hacer operaciones
        
        Ventajas del context manager:
        - Cierra automáticamente la conexión al salir
        - Maneja errores correctamente
        - Más limpio y seguro
        
        Yields:
            cx_Oracle.Connection: Conexión activa a Oracle
        """
        connection = None
        try:
            # Establecer conexión
            logger.debug("Estableciendo conexión con Oracle...")
            connection = cx_Oracle.connect(
                user=self.oracle_user,
                password=self.oracle_password,
                dsn=self.oracle_dsn,
                encoding=self.encoding
            )
            logger.debug("Conexión establecida exitosamente")
            
            yield connection
            
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            logger.error(f"Error de Oracle: {error.code} - {error.message}")
            raise
        
        finally:
            # Cerrar conexión siempre, incluso si hay error
            if connection:
                connection.close()
                logger.debug("Conexión cerrada")
    
    def verificar_flujo_vinculacion(self, numero_cedula):
        """
        Verifica si se creó exitosamente el flujo de vinculación en LINIX.
        
        Este método ejecuta un procedimiento almacenado en Oracle que:
        1. Busca el tercero por número de cédula
        2. Verifica que el flujo se haya creado correctamente
        3. Retorna el ID del tercero y estado
        
        Args:
            numero_cedula (str): Cédula del usuario a verificar
            
        Returns:
            dict: Resultado de la verificación:
                {
                    'exitoso': bool,
                    'encontrado': bool,
                    'id_tercero': str,
                    'estado_flujo': str,
                    'datos_completos': dict,
                    'error': str (solo si exitoso=False)
                }
        
        Example:
            >>> service = LinixService()
            >>> resultado = service.verificar_flujo_vinculacion('123456789')
            >>> if resultado['exitoso'] and resultado['encontrado']:
            >>>     print(f"ID Tercero: {resultado['id_tercero']}")
        """
        
        logger.info(f"Verificando flujo de vinculación para cédula: {numero_cedula}")
        
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                
                # Variables para recibir los valores de salida del procedimiento
                # Ajustar según los parámetros reales de tu procedimiento
                
                # OUT parameters
                out_id_tercero = cursor.var(cx_Oracle.STRING)
                out_estado = cursor.var(cx_Oracle.STRING)
                out_mensaje = cursor.var(cx_Oracle.STRING)
                out_existe = cursor.var(cx_Oracle.NUMBER)
                
                # TODO: Reemplazar con el nombre real de tu procedimiento
                # Ejemplo: PKG_VINCULACION.VERIFICAR_FLUJO(?)
                proc_name = "PKG_VINCULACION.VERIFICAR_FLUJO_CREADO"
                
                # Ejecutar procedimiento almacenado
                # Sintaxis: cursor.callproc(nombre, [parametros])
                cursor.callproc(
                    proc_name,
                    [
                        numero_cedula,        # IN: Cédula a buscar
                        out_id_tercero,       # OUT: ID del tercero
                        out_estado,           # OUT: Estado del flujo
                        out_existe,           # OUT: 1 si existe, 0 si no
                        out_mensaje           # OUT: Mensaje descriptivo
                    ]
                )
                
                # Extraer valores de salida
                existe = out_existe.getvalue()
                id_tercero = out_id_tercero.getvalue()
                estado = out_estado.getvalue()
                mensaje = out_mensaje.getvalue()
                
                cursor.close()
                
                # Registrar resultado
                logger.info(f"Verificación completada: Existe={existe}, ID={id_tercero}")
                
                return {
                    'exitoso': True,
                    'encontrado': existe == 1,
                    'id_tercero': id_tercero if existe == 1 else None,
                    'estado_flujo': estado,
                    'mensaje': mensaje,
                    'datos_completos': {
                        'existe': existe,
                        'id_tercero': id_tercero,
                        'estado': estado,
                        'mensaje': mensaje
                    }
                }
        
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            logger.error(f"Error ejecutando procedimiento: {error.message}")
            return {
                'exitoso': False,
                'error': f'Error de base de datos: {error.message}'
            }
        
        except Exception as e:
            logger.exception(f"Error inesperado en verificación: {str(e)}")
            return {
                'exitoso': False,
                'error': f'Error inesperado: {str(e)}'
            }

    def consultar_actu(self, numero_cedula, fecha_expedicion):
        """
        Ejecuta SP_CONSULTACTU para validar si el ciudadano ya es asociado.

        Args:
            numero_cedula (str): Cédula del ciudadano
            fecha_expedicion (str): Fecha de expedición en formato DD/MM/YYYY

        Returns:
            dict: {
                'exitoso': bool,
                'encontrado': bool,
                'error': str (solo si exitoso=False)
            }
        """
        logger.info(f"Consultando SP_CONSULTACTU para cédula: {numero_cedula}")

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                out_cursor = cursor.var(cx_Oracle.CURSOR)

                cursor.callproc('SP_CONSULTACTU', [numero_cedula, fecha_expedicion, out_cursor])

                result_cursor = out_cursor.getvalue()
                row = result_cursor.fetchone() if result_cursor else None
                logger.info(f"Datos que devuelve SP_CONSULTACTU: {row}")    
                if result_cursor:
                    result_cursor.close()
                cursor.close()

                encontrado = row is not None and str(row[0]) != 'Error'

                return {
                    'exitoso': True,
                    'encontrado': encontrado
                }

        except cx_Oracle.DatabaseError as e:
            error, = e.args
            message = error.message or ''
            if 'ORA-20050' in message or 'No existe el asociado' in message:
                logger.info("SP_CONSULTACTU: asociado no encontrado (se permite continuar)")
                return {
                    'exitoso': True,
                    'encontrado': False
                }
            logger.error(f"Error ejecutando SP_CONSULTACTU: {message}")
            return {
                'exitoso': False,
                'error': f'Error de base de datos: {message}'
            }

        except Exception as e:
            logger.exception(f"Error inesperado en SP_CONSULTACTU: {str(e)}")
            return {
                'exitoso': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def consultar_tercero_por_cedula(self, numero_cedula):
        """
        Consulta directa a la tabla gr_tercero para obtener datos del tercero.
        
        Este método es opcional, por si necesitas hacer consultas SQL directas
        en lugar de usar procedimientos almacenados.
        
        Args:
            numero_cedula (str): Cédula a buscar
            
        Returns:
            dict: Datos del tercero o None si no existe
        """
        
        logger.info(f"Consultando tercero por cédula: {numero_cedula}")
        
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                
                # TODO: Ajustar nombre de tabla y columnas según tu esquema
                query = """
                    SELECT 
                        ID_TERCERO,
                        N_IDENTIFICACION,
                        PRIMER_NOMBRE,
                        SEGUNDO_NOMBRE,
                        PRIMER_APELLIDO,
                        SEGUNDO_APELLIDO,
                        ESTADO
                    FROM GR_TERCERO
                    WHERE N_IDENTIFICACION = :cedula
                    AND ROWNUM = 1
                """
                
                cursor.execute(query, cedula=numero_cedula)
                
                # Obtener nombres de columnas
                columns = [col[0] for col in cursor.description]
                
                # Obtener resultado
                row = cursor.fetchone()
                
                cursor.close()
                
                if row:
                    # Convertir tupla a diccionario
                    resultado = dict(zip(columns, row))
                    logger.info(f"Tercero encontrado: ID={resultado['ID_TERCERO']}")
                    return resultado
                else:
                    logger.info(f"No se encontró tercero con cédula: {numero_cedula}")
                    return None
        
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            logger.error(f"Error consultando tercero: {error.message}")
            return None
        
        except Exception as e:
            logger.exception(f"Error inesperado: {str(e)}")
            return None
    
    def test_connection(self):
        """
        Método de utilidad para probar la conexión a Oracle.
        
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()
                cursor.close()
                
                logger.info("Test de conexión exitoso")
                return True
        
        except Exception as e:
            logger.error(f"Test de conexión falló: {str(e)}")
            return False
