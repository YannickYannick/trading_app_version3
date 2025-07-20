# Configuration Gunicorn pour Django Trading App
import multiprocessing

# Nombre de workers (généralement 2-4 × nombre de CPU)
workers = multiprocessing.cpu_count() * 2 + 1

# Type de worker
worker_class = 'sync'

# Port d'écoute
bind = '127.0.0.1:8000'

# Timeout
timeout = 120

# Logs
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'
loglevel = 'info'

# Process name
proc_name = 'trading_app'

# User/Group (à adapter selon ton serveur)
# user = 'www-data'
# group = 'www-data'

# Preload app
preload_app = True

# Max requests per worker
max_requests = 1000
max_requests_jitter = 50

# Restart workers after max requests
max_requests_jitter = 50 