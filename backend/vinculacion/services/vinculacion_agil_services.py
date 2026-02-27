import logging
from datetime import datetime, date
from urllib.parse import urljoin
import re
import unicodedata
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_SUCURSAL_MAP = {
    "ACACIAS": "103",
    "BARRANCA": "109",
    "BARRANCADEUPIA": "109",
    "CABUYARO": "111",
    "CASTILLALANUEVA": "216",
    "CATAMA": "108",
    "CUBARRAL": "203",
    "CUMARAL": "206",
    "ELCASTILLO": "213",
    "GRANADA": "106",
    "GUAYABETAL": "107",
    "LEJANIAS": "205",
    "MESETAS": "211",
    "MONTECARLO": "105",
    "POPULAR": "102",
    "PORFIA": "104",
    "PRINCIPAL": "101",
    "PUERTOGAITAN": "110",
    "PUERTOLLERAS": "214",
    "PUERTOLOPEZ": "210",
    "PUERTORICO": "204",
    "TAURAMENA": "208",
    "URIBE": "212",
    "VILLANUEVA": "207",
    "VISTAHERMOSA": "112",
    "YOPAL": "209",
}


class VinculacionAgilError(Exception):
    pass


class VinculacionAgilService:
    """
    Servicio para construir la trama de vinculacion agil y enviarla al core LINIX.
    """

    def __init__(self):
        self.base_url = str(
            getattr(settings, "LINIX_API_BASE_URL", "http://consulta.congente.coop:8041")
        ).strip()
        self.token_url = str(getattr(settings, "LINIX_TOKEN_URL", "") or "").strip()
        self.vinculacion_url = str(getattr(settings, "LINIX_VINCULACION_URL", "") or "").strip()
        self.token_path = getattr(settings, "LINIX_TOKEN_PATH", "/api/v1/incluirtec/token/")
        self.vinculacion_path = getattr(
            settings,
            "LINIX_VINCULACION_PATH",
            "/api/v1/incluirtec/vinculacion/"
        )
        self.client_id = getattr(settings, "LINIX_CLIENT_ID", "")
        self.client_secret = getattr(settings, "LINIX_CLIENT_SECRET", "")
        self.timeout = int(getattr(settings, "LINIX_TIMEOUT", 30))
        self.verify_ssl = bool(getattr(settings, "LINIX_VERIFY_SSL", True))
        self.ca_bundle = str(getattr(settings, "LINIX_CA_BUNDLE", "") or "").strip() or None
        self.token_cache_key = getattr(settings, "LINIX_TOKEN_CACHE_KEY", "linix_access_token")
        self.token_safety_seconds = int(getattr(settings, "LINIX_TOKEN_CACHE_SAFETY_SECONDS", 60))
        self.country_code_default = str(getattr(settings, "LINIX_DEFAULT_COUNTRY_CODE", "169"))
        self.autoretenedor_default = str(getattr(settings, "LINIX_DEFAULT_AUTORETENEDOR", "N"))
        self.tipo_con_default = str(getattr(settings, "LINIX_DEFAULT_TIPO_CON", "D"))
        self.tipo_cuenta_default = str(getattr(settings, "LINIX_DEFAULT_TIPO_CUENTA", "A"))
        self.valor_factor_default = str(getattr(settings, "LINIX_DEFAULT_VALOR_FACTOR", "1"))
        self.nit_default = str(getattr(settings, "LINIX_NIT_DEFAULT", "") or "").strip()
        self.sucursal_default = str(getattr(settings, "LINIX_DEFAULT_SUCURSAL", "101") or "101").strip()
        self.catalog_defaults = getattr(settings, "LINIX_CATALOG_DEFAULTS", {})
        self.linix_dry_run = bool(getattr(settings, "LINIX_DRY_RUN", False) and settings.DEBUG)
        self.request_verify = self.ca_bundle if self.ca_bundle else self.verify_ssl
        self.sucursal_map = DEFAULT_SUCURSAL_MAP

    def _build_url(self, path):
        return urljoin(self.base_url.rstrip("/") + "/", str(path).lstrip("/"))

    @staticmethod
    def _full_name(primer_apellido, segundo_apellido, primer_nombre, segundo_nombre):
        parts = [
            str(primer_apellido or "").strip(),
            str(segundo_apellido or "").strip(),
            str(primer_nombre or "").strip(),
            str(segundo_nombre or "").strip(),
        ]
        return " ".join([p for p in parts if p]).upper()

    @staticmethod
    def _string_date(value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _mmddyyyy(value):
        """
        Convierte fecha a formato MM/DD/YYYY requerido por algunos endpoints LINIX.
        """
        if isinstance(value, datetime):
            return value.strftime("%m/%d/%Y")
        if isinstance(value, date):
            return value.strftime("%m/%d/%Y")

        raw = str(value or "").strip()
        if not raw:
            return raw

        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").strftime("%m/%d/%Y")
        except ValueError:
            pass

        try:
            return datetime.strptime(raw[:10], "%m/%d/%Y").strftime("%m/%d/%Y")
        except ValueError:
            return raw

    def _derive_geo_codes(self, ciudad_code):
        city = str(ciudad_code or "").strip()
        dept_code = city[:2] if len(city) >= 2 else str(getattr(settings, "LINIX_DEFAULT_DEPARTMENT_CODE", "11"))
        country = self.country_code_default
        return dept_code, country

    @staticmethod
    def _decimal_to_plain(value):
        """
        Convierte salarios/valores numericos a string sin separadores de miles.
        """
        if value is None:
            return ""

        try:
            parsed = Decimal(str(value))
            if parsed == parsed.to_integral_value():
                return str(int(parsed))
            return format(parsed, "f")
        except (InvalidOperation, ValueError, TypeError):
            return re.sub(r"\D", "", str(value or ""))

    @staticmethod
    def _norm_text(value):
        clean = unicodedata.normalize("NFKD", str(value or ""))
        clean = clean.encode("ascii", "ignore").decode("ascii").upper()
        return re.sub(r"[^A-Z0-9]", "", clean)

    def _resolve_sucursal_code(self, sucursal_raw):
        raw = str(sucursal_raw or "").strip()
        if raw.isdigit():
            return raw
        normalized = self._norm_text(raw)
        return self.sucursal_map.get(normalized, self.sucursal_default)

    def build_trama(self, data, preregistro=None):
        """
        Mapea DTO reducido -> Trama completa para core LINIX.
        """
        identificacion = str(
            data.get("identificacion")
            or getattr(preregistro, "numero_cedula", "")
            or ""
        ).strip()
        fecha_afiliacion_origen = data.get("fechaAfiliacion") or datetime.now().date()
        fecha_afiliacion = self._mmddyyyy(fecha_afiliacion_origen)
        ciudad_code = str(data.get("ciudad") or "").strip() or str(
            getattr(settings, "LINIX_DEFAULT_CITY_CODE", "11001")
        )
        dept_code, country_code = self._derive_geo_codes(ciudad_code)
        nit_asociado = self.nit_default or identificacion
        sucursal_code = self._resolve_sucursal_code(
            data.get("sucursal") or getattr(preregistro, "agencia", None)
        )
        fecha_expedicion = self._mmddyyyy(
            getattr(preregistro, "fecha_expedicion", None) or fecha_afiliacion_origen
        )
        celular = str(data.get("celular") or "").strip()
        telefono = str(data.get("telefono") or celular).strip()
        salario = self._decimal_to_plain(data.get("salario"))
        poblacion_vulnerable = str(data.get("poblacionVulnerable") or "N")
        publico_expuesto = str(data.get("publicamenteExpuesto") or "N")
        operaciones_monext = str(data.get("operacionesMonedaExtranjera") or "N")
        declara_renta = str(data.get("declaraRenta") or "N")
        administra_recursos = str(data.get("administraRecursosPublicos") or "N")
        vinculado_recursos = str(data.get("vinculadoRecursosPublicos") or "N")

        defaults = self.catalog_defaults
        tipo_contrato = str(defaults.get("A_TIPO_CONTRATO", "TI"))
        jornada_laboral = str(defaults.get("A_JORNADA_LABORAL", "1"))
        codigo_banco = str(defaults.get("A_CODIGO_BANCO", "01"))
        factor_rh = str(defaults.get("A_FACTOR_RH", "O+"))
        indicativo = str(defaults.get("A_INDICATIVO", "057"))
        formalidad_negocio = str(defaults.get("A_FORMALIDAD_NEGOCIO", "FOR"))
        autoriza_centrales = str(defaults.get("A_AUTORIZA_CENTRALES", "Y"))
        autoriza_notificacion = str(defaults.get("A_AUTORIZA_NOTIFICACION", "Y"))
        nombre_empresa = str(defaults.get("A_NOMBRE_EMPRESA", "INDEPENDIENTE"))
        codigo_empleado = str(defaults.get("A_CODIGO_EMPLEADO", "0"))

        cliente = {
            "identificacion": identificacion,
            "tipoDocumento": str(data.get("tipoDocumento") or ""),
            "primerNombre": str(data.get("primerNombre") or "").strip().upper(),
            "segundoNombre": str(data.get("segundoNombre") or "").strip().upper(),
            "primerApellido": str(data.get("primerApellido") or "").strip().upper(),
            "segundoApellido": str(data.get("segundoApellido") or "").strip().upper(),
            "fechaNacimiento": self._mmddyyyy(data.get("fechaNacimiento")),
            "genero": str(data.get("genero") or ""),
            "estadoCivil": str(data.get("estadoCivil") or ""),
            "email": str(data.get("email") or "").strip().lower(),
            "numeroCelular": celular,
            "telefono": telefono,
            "salario": salario,
            "estrato": str(data.get("estrato") or ""),
            "nivelEstudio": str(data.get("nivelEstudio") or ""),
            "actividadEconomica": str(data.get("actividadEconomica") or ""),
            "tipoVivienda": str(data.get("tipoVivienda") or ""),
            "factorRH": factor_rh,
            "fechaExpedicion": fecha_expedicion,
            "ciudadExpedicion": ciudad_code,
            "departamentoExpedicion": dept_code,
            "paisExpedicion": country_code,
            "tipoCuenta": self.tipo_cuenta_default,
            "numeroCuenta": str(defaults.get("A_NUMERO_CUENTA", "")),
            "codigoBanco": codigo_banco,
            "tipoContrato": tipo_contrato,
            "jornadaLaboral": jornada_laboral,
            "salarioIntegral": "N",
            "autorizaCentrales": autoriza_centrales,
            "autorizaNotificacion": autoriza_notificacion,
            "actividadCIIU": str(data.get("actividadCIIU") or ""),
            "actividadCIIUSecundaria": str(data.get("actividadCIIUSecundaria") or "000"),
            "ocupacion": str(data.get("ocupacion") or ""),
            "poblacionVulnerable": poblacion_vulnerable,
            "personasCargo": str(data.get("personasCargo") if data.get("personasCargo") is not None else "0"),
            "publicamenteExpuesto": publico_expuesto,
            "mujerCabeza": str(defaults.get("A_MUJER_CABEZA", "N")),
            "responsableHogar": str(defaults.get("A_RESPONSABLE_HOGAR", "N")),
            "operacionesMonedaExtranjera": operaciones_monext,
            "declaraRenta": declara_renta,
            "administraRecursos": administra_recursos,
            "vinculadoRecursosPublicos": vinculado_recursos,
            "fechaIngreso": self._mmddyyyy(defaults.get("A_FECHA_INGRESO", fecha_afiliacion)),
            "fechaVencimientoContrato": str(defaults.get("A_FECHA_VENCIMIENTO_CONTRATO", "")),
            "ciudadNacimiento": str(defaults.get("A_CIUDAD_NACIMIENTO", ciudad_code)),
        }

        contactos = [{
            "tipoDireccion": "C",
            "direccion": str(data.get("direccion") or "").strip().upper(),
            "telefono": telefono,
            "movil": celular,
            "email": str(data.get("email") or "").strip().lower(),
            "ciudad": ciudad_code,
            "barrio": str(data.get("barrio") or "").strip().upper(),
            "extension": str(defaults.get("A_EXTENSION", "")),
            "indicativo": indicativo,
            "direccionCorrespondencia": "Y",
        }]

        laboral = {
            "codigoEmpleado": codigo_empleado,
            "nombreEmpresa": nombre_empresa,
            "tipoContrato": tipo_contrato,
            "fechaIngreso": self._mmddyyyy(defaults.get("A_FECHA_INGRESO", fecha_afiliacion)),
            "fechaVencimiento": str(defaults.get("A_FECHA_VENCIMIENTO", "")),
            "salarioIntegral": "N",
            "jornadaLaboral": jornada_laboral,
            "ciudadEmpresa": str(defaults.get("A_CIUDAD_EMPRESA", ciudad_code)),
            "departamentoEmpresa": str(defaults.get("A_DEPARTAMENTO_EMPRESA", dept_code)),
            "paisEmpresa": str(defaults.get("A_PAIS_EMPRESA", country_code)),
            "telefonoEmpresa": str(defaults.get("A_TELEFONO_EMPRESA", telefono)),
            "direccionEmpresa": str(defaults.get("A_DIRECCION_EMPRESA", str(data.get("direccion") or "").strip().upper())),
            "faxEmpresa": str(defaults.get("A_FAX_EMPRESA", "")),
            "formalidadNegocio": formalidad_negocio,
        }

        trama = {
            "nit": nit_asociado,
            "sucursal": sucursal_code,
            "fechaAfiliacion": fecha_afiliacion,
            "cliente": cliente,
            "contactos": contactos,
            "laboral": laboral,
            "activos": [],
            "pasivos": [],
        }

        required_fields = {
            "nit": trama.get("nit"),
            "sucursal": trama.get("sucursal"),
            "fechaAfiliacion": trama.get("fechaAfiliacion"),
            "cliente.identificacion": cliente.get("identificacion"),
            "cliente.tipoDocumento": cliente.get("tipoDocumento"),
            "cliente.primerNombre": cliente.get("primerNombre"),
            "cliente.primerApellido": cliente.get("primerApellido"),
            "cliente.fechaNacimiento": cliente.get("fechaNacimiento"),
            "cliente.genero": cliente.get("genero"),
            "cliente.estadoCivil": cliente.get("estadoCivil"),
            "cliente.email": cliente.get("email"),
            "cliente.numeroCelular": cliente.get("numeroCelular"),
            "contactos[0].direccion": contactos[0].get("direccion"),
            "contactos[0].ciudad": contactos[0].get("ciudad"),
            "contactos[0].barrio": contactos[0].get("barrio"),
        }
        missing = [
            key for key, value in required_fields.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise VinculacionAgilError(
                "Campos requeridos faltantes para LINIX: " + ", ".join(missing)
            )

        return trama

    def get_linix_token(self, force_refresh=False):
        """
        Obtiene token desde cache y si no existe/expira, lo solicita al core.
        """
        if not force_refresh:
            cached = cache.get(self.token_cache_key)
            if cached:
                return cached

        if not self.client_id or not self.client_secret:
            raise VinculacionAgilError("Credenciales LINIX incompletas en configuracion.")

        token_url = self.token_url or self._build_url(self.token_path)
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        logger.info("Solicitando token LINIX a %s", token_url)
        try:
            response = requests.post(
                token_url,
                json=payload,
                timeout=self.timeout,
                verify=self.request_verify,
            )
        except requests.exceptions.SSLError as exc:
            raise VinculacionAgilError(
                "Error SSL al solicitar token LINIX. "
                "Verifica el certificado del servidor o configura LINIX_CA_BUNDLE. "
                "Solo para pruebas internas: LINIX_VERIFY_SSL=false."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise VinculacionAgilError(
                f"No fue posible conectar con LINIX token endpoint: {exc}"
            ) from exc

        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {}

        if response.status_code != 200:
            raise VinculacionAgilError(
                f"No se pudo obtener token LINIX. HTTP {response.status_code}"
            )

        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        result_code = data.get("result")
        if not access_token:
            raise VinculacionAgilError(
                data.get("message") or "Respuesta invalida al solicitar token LINIX."
            )
        if result_code is not None and str(result_code) != "0":
            raise VinculacionAgilError(
                data.get("message") or f"Error LINIX token result={result_code}."
            )

        ttl = max(expires_in - self.token_safety_seconds, 60)
        cache.set(self.token_cache_key, access_token, ttl)
        return access_token

    def send_linix_vinculacion(self, payload):
        """
        Envia la trama al core LINIX. Reintenta una vez en caso 401/403.
        """
        if self.linix_dry_run:
            return {
                "status_code": 200,
                "response_data": {
                    "result": 0,
                    "message": "Vinculacion simulada en modo local (LINIX_DRY_RUN).",
                    "radicado": f"DRY-{payload.get('cliente', {}).get('identificacion', 'N/A')}",
                },
            }

        vinc_url = self.vinculacion_url or self._build_url(self.vinculacion_path)
        token = self.get_linix_token()

        def _do_request(current_token):
            try:
                return requests.post(
                    vinc_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {current_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=self.timeout,
                    verify=self.request_verify,
                )
            except requests.exceptions.SSLError as exc:
                raise VinculacionAgilError(
                    "Error SSL al enviar vinculacion a LINIX. "
                    "Verifica el certificado del servidor o configura LINIX_CA_BUNDLE. "
                    "Solo para pruebas internas: LINIX_VERIFY_SSL=false."
                ) from exc
            except requests.exceptions.RequestException as exc:
                raise VinculacionAgilError(
                    f"No fue posible conectar con LINIX vinculacion endpoint: {exc}"
                ) from exc

        response = _do_request(token)
        if response.status_code in {401, 403}:
            token = self.get_linix_token(force_refresh=True)
            response = _do_request(token)

        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {"raw": response.text[:5000] if response.text else ""}

        ok = 200 <= response.status_code < 300
        if not ok:
            msg = data.get("message") if isinstance(data, dict) else None
            raise VinculacionAgilError(
                msg or f"Error LINIX HTTP {response.status_code}"
            )

        return {
            "status_code": response.status_code,
            "response_data": data,
        }
