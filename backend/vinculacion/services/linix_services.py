# vinculacion/services/linix_service.py

"""
SERVICIO DE INTEGRACION CON ORACLE/LINIX
=========================================
Maneja la conexion con la base de datos Oracle
y la ejecucion de procedimientos almacenados.
"""

import oracledb
import logging
from django.conf import settings
from contextlib import contextmanager

# Configurar logger
logger = logging.getLogger(__name__)


class LinixService:
    """
    Servicio para interactuar con la base de datos Oracle de LINIX.
    
    Este servicio encapsula:
    - Conexion a Oracle
    - Ejecucion de procedimientos almacenados
    - Manejo de errores de BD
    """
    
    def __init__(self):
        """
        Constructor del servicio.
        
        Inicializa los parametros de conexion desde settings.py
        """
        self.oracle_user = getattr(settings, 'ORACLE_USER', '')
        self.oracle_password = getattr(settings, 'ORACLE_PASSWORD', '')
        self.oracle_dsn = getattr(settings, 'ORACLE_DSN', '')  # host:port/service_name
        
        # Configuracion de encoding
    
    @contextmanager
    def get_connection(self):
        """
        Context manager para manejar conexiones a Oracle.
        
        Uso:
            with service.get_connection() as connection:
                cursor = connection.cursor()
                # hacer operaciones
        
        Ventajas del context manager:
        - Cierra automaticamente la conexion al salir
        - Maneja errores correctamente
        - Mas limpio y seguro
        
        Yields:
            oracledb.Connection: Conexion activa a Oracle
        """
        connection = None
        try:
            # Establecer conexion
            logger.debug("Estableciendo conexion con Oracle...")
            connection = oracledb.connect(
                user=self.oracle_user,
                password=self.oracle_password,
                dsn=self.oracle_dsn
            )
            logger.debug("Conexion establecida exitosamente")
            
            yield connection
            
        except oracledb.DatabaseError as e:
            error, = e.args
            logger.error(f"Error de Oracle: {error.code} - {error.message}")
            raise
        
        finally:
            # Cerrar conexion siempre, incluso si hay error
            if connection:
                connection.close()
                logger.debug("Conexion cerrada")
    
    def verificar_flujo_vinculacion(self, numero_cedula):
        """
        Verifica si se creo exitosamente el flujo de vinculacion en LINIX.

        Este metodo ejecuta SP_FLUJOEXITOSO(cedula), donde:
        - OK: el flujo se creo correctamente
        - PDTE: el flujo no se creo aun o presenta alguna novedad

        Args:
            numero_cedula (str): Cedula del usuario a verificar

        Returns:
            dict: Resultado de la verificacion
        """

        logger.info(f"Verificando flujo de vinculacion para cedula: {numero_cedula}")
        dry_run = bool(getattr(settings, 'LINIX_VERIFICACION_DRY_RUN', False) and settings.DEBUG)
        if dry_run:
            return {
                'exitoso': True,
                'encontrado': True,
                'id_tercero': f"DRY-{numero_cedula}",
                'estado_flujo': 'OK',
                'mensaje': 'Flujo confirmado en modo de prueba local.',
                'datos_completos': {
                    'procedimiento': 'SP_FLUJOEXITOSO',
                    'cedula': str(numero_cedula),
                    'estado': 'OK',
                    'id_tercero': f"DRY-{numero_cedula}",
                    'dry_run': True,
                }
            }

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                proc_name = "SP_FLUJOEXITOSO"
                out_estado = cursor.var(oracledb.DB_TYPE_VARCHAR)
                cursor.callproc(proc_name, [str(numero_cedula), out_estado])
                estado_raw = out_estado.getvalue()

                estado = str(estado_raw).strip().upper() if estado_raw is not None else ""

                if estado not in {"OK", "PDTE"}:
                    cursor.close()
                    logger.error(
                        "Respuesta inesperada en %s para cedula %s: %s",
                        proc_name,
                        numero_cedula,
                        estado_raw
                    )
                    return {
                        'exitoso': False,
                        'error': (
                            f'Respuesta inesperada de {proc_name}: '
                            f'{estado_raw!r}'
                        ),
                        'datos_completos': {
                            'procedimiento': proc_name,
                            'cedula': str(numero_cedula),
                            'estado': estado,
                            'estado_raw': estado_raw
                        }
                    }

                encontrado = estado == "OK"
                mensaje = (
                    "Flujo confirmado en LINIX."
                    if encontrado
                    else "Flujo pendiente en LINIX o con novedad (PDTE)."
                )
                # En este flujo solo se consulta el SP; no se hace SELECT adicional.
                id_tercero = None

                cursor.close()

                logger.info(
                    "Verificacion %s completada para cedula %s: estado=%s, id_tercero=%s",
                    proc_name,
                    numero_cedula,
                    estado,
                    id_tercero
                )

                return {
                    'exitoso': True,
                    'encontrado': encontrado,
                    'id_tercero': id_tercero,
                    'estado_flujo': estado,
                    'mensaje': mensaje,
                    'datos_completos': {
                        'procedimiento': proc_name,
                        'cedula': str(numero_cedula),
                        'estado': estado,
                        'id_tercero': id_tercero,
                        'mensaje': mensaje
                    }
                }

        except oracledb.DatabaseError as e:
            error, = e.args
            logger.error(f"Error ejecutando procedimiento SP_FLUJOEXITOSO: {error.message}")
            return {
                'exitoso': False,
                'error': f'Error de base de datos: {error.message}'
            }

        except Exception as e:
            logger.exception(f"Error inesperado en verificacion: {str(e)}")
            return {
                'exitoso': False,
                'error': f'Error inesperado: {str(e)}'
            }

    def consultar_actu(self, numero_cedula, fecha_expedicion):
        """
        Ejecuta SP_CONSULTACTU para validar si el ciudadano ya es asociado.

        Args:
            numero_cedula (str): Cedula del ciudadano
            fecha_expedicion (str): Fecha de expedicion en formato DD/MM/YYYY

        Returns:
            dict: {
                'exitoso': bool,
                'encontrado': bool,
                'error': str (solo si exitoso=False)
            }
        """
        logger.info(f"Consultando SP_CONSULTACTU para cedula: {numero_cedula}")

        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                out_cursor = cursor.var(oracledb.DB_TYPE_CURSOR)

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

        except oracledb.DatabaseError as e:
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
        
        Este metodo es opcional, por si necesitas hacer consultas SQL directas
        en lugar de usar procedimientos almacenados.
        
        Args:
            numero_cedula (str): Cedula a buscar
            
        Returns:
            dict: Datos del tercero o None si no existe
        """
        
        logger.info(f"Consultando tercero por cedula: {numero_cedula}")
        
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                
                # TODO: Ajustar nombre de tabla y columnas segun tu esquema
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
                    logger.info(f"No se encontro tercero con cedula: {numero_cedula}")
                    return None
        
        except oracledb.DatabaseError as e:
            error, = e.args
            logger.error(f"Error consultando tercero: {error.message}")
            return None
        
        except Exception as e:
            logger.exception(f"Error inesperado: {str(e)}")
            return None
    
    def test_connection(self):
        """
        Metodo de utilidad para probar la conexion a Oracle.
        
        Returns:
            bool: True si la conexion fue exitosa
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()
                cursor.close()
                
                logger.info("Test de conexion exitoso")
                return True
        
        except Exception as e:
            logger.error(f"Test de conexion fallo: {str(e)}")
            return False



