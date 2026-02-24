import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


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
        self.token_cache_key = getattr(settings, "LINIX_TOKEN_CACHE_KEY", "linix_access_token")
        self.token_safety_seconds = int(getattr(settings, "LINIX_TOKEN_CACHE_SAFETY_SECONDS", 60))
        self.country_code_default = str(getattr(settings, "LINIX_DEFAULT_COUNTRY_CODE", "169"))
        self.autoretenedor_default = str(getattr(settings, "LINIX_DEFAULT_AUTORETENEDOR", "N"))
        self.tipo_con_default = str(getattr(settings, "LINIX_DEFAULT_TIPO_CON", "D"))
        self.tipo_cuenta_default = str(getattr(settings, "LINIX_DEFAULT_TIPO_CUENTA", "A"))
        self.valor_factor_default = str(getattr(settings, "LINIX_DEFAULT_VALOR_FACTOR", "1"))
        self.catalog_defaults = getattr(settings, "LINIX_CATALOG_DEFAULTS", {})
        self.linix_dry_run = bool(getattr(settings, "LINIX_DRY_RUN", False) and settings.DEBUG)

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
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    def _derive_geo_codes(self, ciudad_code):
        city = str(ciudad_code or "").strip()
        dept_code = city[:2] if len(city) >= 2 else str(getattr(settings, "LINIX_DEFAULT_DEPARTMENT_CODE", "11"))
        country = self.country_code_default
        return dept_code, country

    def build_trama(self, data):
        """
        Mapea DTO reducido -> Trama completa para core LINIX.
        """
        fecha_afiliacion = self._string_date(data["fechaAfiliacion"])
        dept_code, country_code = self._derive_geo_codes(data["ciudad"])

        trama = {
            "A_ACTIVO": "Y",
            "A_ASOCON": "1",
            "A_AUTORETENEDOR": self.autoretenedor_default,
            "A_EMPRESA": "0",
            "A_ESTADO_CLIENTE": "A",
            "A_FUNCIONALIDAD": "6",
            "A_NATURALEZA": "N",
            "A_NOMINA": "999",
            "A_TIPASO": "5",
            "A_TIPO_CON": self.tipo_con_default,
            "A_TIPO_CUENTA": self.tipo_cuenta_default,
            "A_TIPO_DOC": str(data["tipoDocumento"]),
            "A_CODIGO_CLIENTE": str(data["identificacion"]),
            "F_NACIMIENTO": self._string_date(data["fechaNacimiento"]),
            "A_PRIMER_NOMBRE": str(data["primerNombre"]).strip().upper(),
            "A_SEGUNDO_NOMBRE": str(data.get("segundoNombre") or "").strip().upper(),
            "A_PRIMER_APELLIDO": str(data["primerApellido"]).strip().upper(),
            "A_SEGUNDO_APELLIDO": str(data.get("segundoApellido") or "").strip().upper(),
            "A_NOMBRE": self._full_name(
                data["primerApellido"],
                data.get("segundoApellido"),
                data["primerNombre"],
                data.get("segundoNombre"),
            ),
            "A_GENERO": str(data["genero"]),
            "A_ESTADO_CIVIL": str(data["estadoCivil"]),
            "A_EMAIL": str(data["email"]).strip().lower(),
            "A_NUM_CELULAR": str(data["celular"]).strip(),
            "A_TELEFONO": str(data.get("telefono") or "").strip(),
            "A_SUCURSAL": str(data["sucursal"]),
            "F_ANTIGUEDAD": fecha_afiliacion,
            "F_PRIMERA_AFILIA": fecha_afiliacion,
            "F_ULTIMA_AFILIA": fecha_afiliacion,
            "F_APROBACION": fecha_afiliacion,
            "A_UBICACION_UNO": str(self.catalog_defaults.get("A_UBICACION_UNO", "1")),
            "A_UBICACION_DOS": str(self.catalog_defaults.get("A_UBICACION_DOS", "1")),
            "A_SECCION": str(self.catalog_defaults.get("A_SECCION", "1")),
            "A_CENCOS": str(self.catalog_defaults.get("A_CENCOS", "1")),
            "A_CARGO": str(self.catalog_defaults.get("A_CARGO", "1")),
            "A_DEPENDENCIA": str(self.catalog_defaults.get("A_DEPENDENCIA", "1")),
            "R_Contacto": {
                "A_TIPO_DIRECCION": "C",
                "A_DIRECCION_CONTACTO": str(data["direccion"]).strip().upper(),
                "A_BARRIO": str(data["barrio"]).strip().upper(),
                "A_CIUDAD_DIR": str(data["ciudad"]).strip(),
                "A_CODIGO_DEPART": dept_code,
                "A_CODIGO_PAIS": country_code,
            },
            "R_Estatutarias": {
                "V_VALOR_FACTOR": self.valor_factor_default,
            },
            "R_Financiera": {
                "A_OPERACIONES_MONEXT": str(data["operacionesMonedaExtranjera"]),
                "A_DECLARA_RENTA": str(data["declaraRenta"]),
                "A_ADMINTRA_RECURSOS": str(data["administraRecursosPublicos"]),
                "I_VINCULADO_RECPU": str(data["vinculadoRecursosPublicos"]),
            },
            "R_Socioeconomica": {
                "A_ESTRATO": int(data["estrato"]),
                "A_TIPO_VIVIENDA": str(data["tipoVivienda"]),
                "A_NIVEL_ESTUDIO": str(data["nivelEstudio"]),
                "A_ACTIVIDAD_ECONOMICA": str(data["actividadEconomica"]),
                "A_OCUPACION": str(data["ocupacion"]),
                "A_ACTIVIDAD_CIIU": str(data["actividadCIIU"]),
                "A_ACTIVIDAD_CIIU_SECU": str(data["actividadCIIUSecundaria"]),
                "A_POBVULNERABLE": str(data["poblacionVulnerable"]),
                "A_PUBEXP": str(data["publicamenteExpuesto"]),
                "A_NUM_PERCARGO": int(data["personasCargo"]),
                "V_SUELDO_ASOC": str(data["salario"]),
            },
            "R_Laboral": {
                "A_ESTADO_LABORAL": str(self.catalog_defaults.get("A_ESTADO_LABORAL", "A")),
                "A_TIPO_CONTRATO": str(self.catalog_defaults.get("A_TIPO_CONTRATO", "01")),
            },
            "R_Activos": [],
            "R_Pasivos": [],
        }

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
        response = requests.post(token_url, json=payload, timeout=self.timeout)

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
                    "radicado": f"DRY-{payload.get('A_CODIGO_CLIENTE', 'N/A')}",
                },
            }

        vinc_url = self.vinculacion_url or self._build_url(self.vinculacion_path)
        token = self.get_linix_token()

        def _do_request(current_token):
            return requests.post(
                vinc_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {current_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )

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
