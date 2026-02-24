# Backend - Vinculacion Digital

Esta carpeta contiene el backend en Django/DRF para el flujo de vinculacion digital. Este README resume el flujo completo, ejemplos, archivos tocados y puntos de mantenimiento.

## Flujo completo (resumen)

1) Pre-registro (Paso 1)
- Endpoint: `POST /api/v1/preregistro/iniciar/`
- Accion:
  - Valida datos basicos.
  - Consulta Oracle via `SP_CONSULTACTU` con cedula + fecha expedicion.
  - Si el ciudadano YA es asociado, se bloquea el pre-registro.
  - Si NO es asociado, crea registro en DECRIM y retorna el link.

2) Validacion identidad (Paso 2)
- El usuario sigue el link DECRIM.
- DECRIM valida identidad y finaliza el proceso.
- Opcional: Webhook DECRIM segun "DTI_Usuario API Standard WebHook v1.0"
  (endpoints `POST /api/v1/decrim/token/` y `POST /api/v1/decrim/webhook/`).
  Si no se usa webhook, el estado se consulta via polling.

3) Link LINIX (Paso 3)
- Endpoint: `GET /api/v1/preregistro/{id}/link-linix/`
- Se habilita cuando la biometria esta aprobada.
- Endpoint adicional Paso 3.2: `POST /api/v1/vinculacion-agil/`
  - Recibe DTO reducido del front.
  - Construye trama completa en backend.
  - Solicita token a LINIX y envia la vinculacion por API.

4) Verificacion LINIX / Oracle (Paso 4)
- Endpoint: `POST /api/v1/preregistro/{id}/verificar-linix/`
- Ejecuta `SP_FLUJOEXITOSO(cedula)` en Oracle para confirmar el resultado del flujo (`OK` o `PDTE`).
- Si retorna `OK`, marca completado (y opcionalmente dispara webhook N8N si esta configurado). Si retorna `PDTE`, mantiene el flujo pendiente.

5) Verificacion periodica LINIX / Oracle (Paso 5)
- Endpoint: `POST /api/v1/linix/verificar-pendientes/`
- Se usa desde n8n cada 10 minutos para consultar Oracle.
- Retorna la lista de preregistros completados para notificacion.

## Ejemplos (requests)

### Paso 1 - Iniciar preregistro

```bash
curl -X POST http://127.0.0.1:8000/api/v1/preregistro/iniciar/ \
  -H "Content-Type: application/json" \
  -d "{\"numero_cedula\":\"123456789\",\"nombres_completos\":\"Juan Perez\",\"fecha_expedicion\":\"2010-05-20\",\"agencia\":\"Bogota\",\"tipo_documento\":1}"
```

Respuesta esperada (si NO es asociado):
- `url_biometria` con el link de DECRIM
- `idcaso_biometria` con el Codigo de DECRIM

Respuesta esperada (si YA es asociado):
- HTTP 400 con mensaje de bloqueo

### Paso 2 - Estado biometria (actual)

> Nota: el polling se mantuvo solo para compatibilidad. La validacion real queda pendiente del callback de DECRIM.

```bash
curl http://127.0.0.1:8000/api/v1/preregistro/1/estado-biometria/
```

### Paso 3 - Link LINIX

```bash
curl http://127.0.0.1:8000/api/v1/preregistro/1/link-linix/
```

### Paso 3.2 - Vinculacion agil (API LINIX)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/vinculacion-agil/ \
  -H "Content-Type: application/json" \
  -d '{"preregistroId":1,"tipoDocumento":"C","identificacion":"1006442327","primerNombre":"LUIS","primerApellido":"GARCIA","fechaNacimiento":"1995-01-15","genero":"M","estadoCivil":"S","email":"luis@email.com","celular":"3001234567","direccion":"CALLE 1 # 2-3","barrio":"CENTRO","ciudad":"11001","estrato":3,"tipoVivienda":"P","nivelEstudio":"U","actividadEconomica":"EM","ocupacion":"1","actividadCIIU":"0122","actividadCIIUSecundaria":"0121","poblacionVulnerable":"N","publicamenteExpuesto":"N","personasCargo":0,"salario":"2500000","operacionesMonedaExtranjera":"N","declaraRenta":"N","administraRecursosPublicos":"N","vinculadoRecursosPublicos":"N","sucursal":"102","fechaAfiliacion":"2026-04-02"}'
```

### Paso 4 - Verificar LINIX

```bash
curl -X POST http://127.0.0.1:8000/api/v1/preregistro/1/verificar-linix/
```

### Paso 5 - Verificacion periodica LINIX (n8n)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/linix/verificar-pendientes/ \
  -H "Content-Type: application/json" \
  -d "{\"limit\":50}"
```

## Archivos tocados (cambios recientes)

- `backend/core/settings.py`
  - Nuevas variables para DECRIM y Oracle.
- `backend/.env`
  - Agregado `DECRIM_API_URL` y se reutilizan credenciales DECRIM.
- `backend/vinculacion/models.py`
  - Campos nuevos: `tipo_documento`, `url_biometria`.
  - Nuevo tipo de log: `REGISTRO_DECRIM`.
- `backend/vinculacion/serializers.py`
  - `tipo_documento` requerido.
  - `link_biometria` ahora usa `url_biometria`.
- `backend/vinculacion/views.py`
  - Bloqueo en Paso 1 usando `SP_CONSULTACTU`.
  - Creacion de registro DECRIM.
- `backend/vinculacion/services/linix_services.py`
  - Metodo `consultar_actu()` con `SP_CONSULTACTU`.
- `backend/vinculacion/services/biometria_services.py`
  - Metodo `crear_registro_decrim()`.
- `backend/vinculacion/migrations/0003_preregistro_tipo_documento_url_biometria.py`
  - Migracion para nuevos campos.

## Donde se bloquea el preregistro

En `backend/vinculacion/views.py`, clase `IniciarPreRegistroView`:
- Se llama `LinixService.consultar_actu()` antes de guardar.
- Si `encontrado=True`, se retorna HTTP 400 y se detiene el flujo.

## Puntos de mantenimiento (donde tocar)

1) DECRIM (registro digital)
- `backend/vinculacion/services/biometria_services.py`
  - Metodo `crear_registro_decrim()`
  - Cambiar URL/credenciales con variables `DECRIM_*`.
- `backend/vinculacion/models.py`
  - Campo `url_biometria` para guardar link.

2) Oracle
- `backend/vinculacion/services/linix_services.py`
  - Metodo `consultar_actu()` (SP_CONSULTACTU)
  - Metodo `verificar_flujo_vinculacion()` (`SP_FLUJOEXITOSO`)

3) LINIX link
- `backend/vinculacion/serializers.py`
  - `get_link_linix()` (URL base y parametros)

4) N8N
- `backend/vinculacion/views.py`
  - Metodo `_enviar_webhook_n8n()`
  - El flujo programado consulta `POST /api/v1/linix/verificar-pendientes/`

## Variables principales

Para produccion (PostgreSQL + Oracle + DECRIM), configurar:
- `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`
- `DECRIM_API_URL`, `DECRIM_USERNAME`, `DECRIM_PASSWORD`
 - `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

### Variables de pruebas locales (dry-run)

Solo aplican si `DEBUG=True`:

- `DEV_SKIP_DECRIM=true`  
  Omite la creacion real del caso en DECRIM durante Paso 1.
- `DEV_BIOMETRIA_AUTO_APPROVE=true`  
  Auto-aprueba biometria para avanzar al Paso 3.
- `LINIX_DRY_RUN=true`  
  Simula el envio de vinculacion agil al core LINIX (Paso 3.2).
- `LINIX_VERIFICACION_DRY_RUN=true`  
  Simula `SP_FLUJOEXITOSO=OK` en Paso 4.

### URLs de prueba

- API local: `http://127.0.0.1:8000/api/v1/`
- Frontend local: `http://localhost:5173`

## Produccion

- Base de datos PostgreSQL lista para montarse en servidor.
- Ajustar `backend/.env` (DECRIM, Oracle, N8N).
- Configurar `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS`.

## Checklist rapido para validar flujo

1) `python manage.py migrate`
2) `python manage.py runserver 127.0.0.1:8000`
3) Crear preregistro (Paso 1) con `tipo_documento`
4) Abrir `url_biometria` (DECRIM)
5) Verificar LINIX (Paso 4)

## Pendientes

- El webhook de DECRIM esta implementado, pero es opcional y solo aplica si
  DECRIM envia notificaciones en tiempo real.

