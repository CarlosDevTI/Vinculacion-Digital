# VinculacionDigital – despliegue con Gunicorn (socket Unix) y Nginx SSL

## Por qué separar contenedores/servicios
- Backend (Django), frontend (build estático) y base de datos (Postgres) tienen ciclos de vida distintos y dependencias diferentes; aislarlos simplifica despliegues y rollbacks.
- Permite escalar cada parte según carga (p.ej. más workers de Gunicorn sin tocar Postgres).
- Seguridad: el proceso web no comparte runtime con la base de datos ni con el servidor estático.

## Componentes esperados
- Django + Gunicorn sirviendo vía socket Unix: `/opt/VinculacionDigital/vinculaciondigital.sock`.
- Nginx como proxy inverso SSL en puerto 8040 para `consulta.congente.coop`.
- Postgres como base de datos (externo o contenedor separado).
- (Opcional) Un contenedor/servicio Nginx distinto para el build de React si se separa el frontend.

## Rutas y supuestos
- Código en `/opt/VinculacionDigital`.
- Entorno virtual en `/opt/VinculacionDigital/venv`.
- Staticfiles colectados en `/opt/VinculacionDigital/static/`.
- Usuario de servicio: `www-data` (ajusta si usas otro).

## systemd: socket y servicio Gunicorn

`/etc/systemd/system/vinculaciondigital.socket`
```
[Unit]
Description=VinculacionDigital Gunicorn socket

[Socket]
ListenStream=/opt/VinculacionDigital/vinculaciondigital.sock
SocketUser=www-data
SocketGroup=www-data
SocketMode=0660

[Install]
WantedBy=sockets.target
```

`/etc/systemd/system/vinculaciondigital.service`
```
[Unit]
Description=VinculacionDigital Gunicorn daemon
Requires=vinculaciondigital.socket
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/VinculacionDigital/backend
Environment="DJANGO_SETTINGS_MODULE=core.settings"
Environment="DJANGO_DEBUG=False"
Environment="DJANGO_SECRET_KEY=<pon_aqui_un_secret>"
Environment="DB_NAME=<db_name>"
Environment="DB_USER=<db_user>"
Environment="DB_PASSWORD=<db_password>"
Environment="DB_HOST=<db_host>"
Environment="DB_PORT=5432"
ExecStart=/opt/VinculacionDigital/venv/bin/gunicorn \
  --workers 3 \
  --bind unix:/opt/VinculacionDigital/vinculaciondigital.sock \
  core.wsgi:application
Restart=always
RuntimeDirectory=gunicorn
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
```

Comandos básicos:
```
sudo systemctl daemon-reload
sudo systemctl enable --now vinculaciondigital.socket vinculaciondigital.service
sudo systemctl status vinculaciondigital.service
```

## Nginx (SSL, puerto 8040)

`/etc/nginx/sites-available/vinculaciondigital`
```
upstream vinculaciondigital_app {
    server unix:/opt/VinculacionDigital/vinculaciondigital.sock;
}

server {
    listen 8040 ssl;
    server_name consulta.congente.coop;

    ssl_certificate /etc/letsencrypt/live/consulta.congente.coop/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/consulta.congente.coop/privkey.pem;

    # Seguridad básica
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Archivos estáticos
    location /static/ {
        alias /opt/VinculacionDigital/static/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    # Proxy a Django
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://vinculaciondigital_app;
    }
}
```

Activar sitio y probar:
```
sudo ln -s /etc/nginx/sites-available/vinculaciondigital /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Postgres (sustituir SQLite)
En `core/settings.py` define la DB con variables de entorno (recomendado):
```
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}
```
Luego:
```
python manage.py migrate
python manage.py collectstatic
```

## Flujo de despliegue rápido
1) Copia código a `/opt/VinculacionDigital` y crea venv.  
2) Instala dependencias `pip install -r backend/requirements.txt`.  
3) Exporta variables de entorno (SECRET_KEY, DB_*).  
4) `python manage.py migrate && python manage.py collectstatic`.  
5) Crea socket/servicio systemd (arriba) y habilítalos.  
6) Configura Nginx (arriba), prueba y recarga.  
7) Probar en `https://consulta.congente.coop:8040/` (o con hosts si aún no apunta DNS).
