# Production deployment (Django 5.2 LTS + MySQL via PyMySQL)

## 1. Server packages (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential pkg-config \
  default-libmysqlclient-dev nginx redis-server
```

## 2. MySQL database

```sql
CREATE DATABASE futnetnepal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'futnet_user'@'localhost' IDENTIFIED BY 'your-strong-password';
GRANT ALL PRIVILEGES ON futnetnepal.* TO 'futnet_user'@'localhost';
FLUSH PRIVILEGES;
```

## 3. Application setup

```bash
cd /var/www/futnetnepal
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.production.example .env
# Edit .env — set SECRET_KEY, DB_*, ALLOWED_HOSTS, REDIS_URL, email, SMS token
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 4. Django commands

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 5. Run with Gunicorn (HTTP) + Daphne (WebSockets)

**HTTP (REST + web):**

```bash
gunicorn futnetnepal.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 3 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

**WebSockets (separate process):**

```bash
daphne -b 127.0.0.1 -p 8001 futnetnepal.asgi:application
```

Point nginx:
- `/` and `/api/` → Gunicorn `:8000`
- `/ws/` → Daphne `:8001` (upgrade headers)

Set `REDIS_URL` in `.env` so all workers share channel layers.

## 6. Nginx (snippet)

```nginx
server {
    listen 443 ssl http2;
    server_name futnetnepal.com www.futnetnepal.com;

    location /static/ {
        alias /var/www/futnetnepal/staticfiles/;
    }
    location /media/ {
        alias /var/www/futnetnepal/media/;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 7. systemd example

See `deploy/futnet-gunicorn.service.example` and `deploy/futnet-daphne.service.example`.

## Environment checklist

| Variable | Production |
|----------|------------|
| `DEBUG` | `False` |
| `USE_SQLITE` | `False` |
| `DB_ENGINE` | `django.db.backends.mysql` |
| `ALLOWED_HOSTS` | Your domain(s) + server IP |
| `CSRF_TRUSTED_ORIGINS` | `https://your-domain` |
| `REDIS_URL` | Required for real-time features |
| `SECRET_KEY` | Unique, never commit |
