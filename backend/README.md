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
- DECRIM valida identidad y finaliza el proceso (callback pendiente de integrar).

3) Link LINIX (Paso 3)
- Endpoint: `GET /api/v1/preregistro/{id}/link-linix/`
- Se habilita cuando la biometria esta aprobada.

4) Verificacion LINIX / Oracle (Paso 4)
- Endpoint: `POST /api/v1/preregistro/{id}/verificar-linix/`
- Ejecuta procedimiento en Oracle para confirmar creacion del tercero.
- Si existe, marca completado y dispara webhook N8N.

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

### Paso 4 - Verificar LINIX

```bash
curl -X POST http://127.0.0.1:8000/api/v1/preregistro/1/verificar-linix/
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
  - Metodo `verificar_flujo_vinculacion()` (procedimiento LINIX)

3) LINIX link
- `backend/vinculacion/serializers.py`
  - `get_link_linix()` (URL base y parametros)

4) N8N
- `backend/vinculacion/views.py`
  - Metodo `_enviar_webhook_n8n()`

## Variables principales

Para produccion (PostgreSQL + Oracle + DECRIM), configurar:
- `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`
- `DECRIM_API_URL`, `DECRIM_USERNAME`, `DECRIM_PASSWORD`
 - `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

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

- Implementar callback de DECRIM (actualmente el backend solo crea el registro y entrega la URL).
