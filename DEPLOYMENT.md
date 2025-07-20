# Guide de Déploiement en Production

## Prérequis

### 1. Serveur Linux (Ubuntu/Debian recommandé)
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Python 3.8+
```bash
sudo apt install python3 python3-pip python3-venv
```

### 3. PostgreSQL
```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres createdb trading_app_prod
sudo -u postgres createuser --interactive
```

### 4. Redis (optionnel mais recommandé)
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
```

### 5. Nginx
```bash
sudo apt install nginx
```

## Configuration

### 1. Variables d'environnement
```bash
cp env.production .env
# Éditer .env avec tes vraies valeurs
```

### 2. Environnement virtuel
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Base de données
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Fichiers statiques
```bash
python manage.py collectstatic
```

## Déploiement

### 1. Script automatique
```bash
chmod +x deploy.sh
./deploy.sh
```

### 2. Manuel
```bash
# Installer les dépendances
pip install -r requirements.txt

# Migrations
python manage.py migrate

# Collecter les statiques
python manage.py collectstatic --noinput

# Tester la configuration
python manage.py check --deploy
```

## Serveur Web

### 1. Gunicorn
```bash
# Démarrer Gunicorn
gunicorn --config gunicorn.conf.py site_trading_v3.wsgi:application

# Ou en arrière-plan
nohup gunicorn --config gunicorn.conf.py site_trading_v3.wsgi:application &
```

### 2. Nginx Configuration
Créer `/etc/nginx/sites-available/trading_app`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /static/ {
        alias /var/www/staticfiles/;
    }

    location /media/ {
        alias /var/www/media/;
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

Activer le site:
```bash
sudo ln -s /etc/nginx/sites-available/trading_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Process Manager (systemd)

Créer `/etc/systemd/system/trading_app.service`:
```ini
[Unit]
Description=Trading App Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/project/venv/bin"
ExecStart=/path/to/your/project/venv/bin/gunicorn --config gunicorn.conf.py site_trading_v3.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Activer le service:
```bash
sudo systemctl enable trading_app
sudo systemctl start trading_app
sudo systemctl status trading_app
```

## Sécurité

### 1. Firewall
```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 2. SSL/HTTPS (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 3. Permissions
```bash
sudo chown -R www-data:www-data /var/www/
sudo chmod -R 755 /var/www/
```

## Monitoring

### 1. Logs
```bash
# Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Application logs
tail -f /path/to/your/project/logs/django.log
```

### 2. Status des services
```bash
sudo systemctl status nginx
sudo systemctl status trading_app
sudo systemctl status postgresql
sudo systemctl status redis-server
```

## Maintenance

### 1. Mise à jour
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart trading_app
```

### 2. Sauvegarde
```bash
# Base de données
pg_dump trading_app_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Fichiers
tar -czf backup_files_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/your/project
```

## Résolution de problèmes

### Erreurs communes
1. **Permission denied** → Vérifier les permissions des fichiers
2. **Database connection** → Vérifier la configuration PostgreSQL
3. **Static files not found** → Vérifier STATIC_ROOT et collectstatic
4. **CSRF errors** → Vérifier ALLOWED_HOSTS et CSRF_TRUSTED_ORIGINS

### Debug
```bash
# Mode debug temporaire
export DJANGO_SETTINGS_MODULE=site_trading_v3.settings.development
python manage.py runserver 0.0.0.0:8000
``` 