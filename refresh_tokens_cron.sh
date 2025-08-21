#!/bin/bash

# Script pour lancer le refresh des tokens depuis un cron
# Usage: ./refresh_tokens_cron.sh [user] [broker]

# Configuration
PROJECT_DIR="/c/Users/Yannick-ConceptD/Documents/Projet - site trading/Trading_app_version3/trading_app_version3"
VENV_ACTIVATE="$PROJECT_DIR/venv/Scripts/Activate.ps1"
MANAGE_PY="$PROJECT_DIR/manage.py"

# Logs
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/refresh_tokens_$(date +%Y%m%d_%H%M%S).log"

# Créer le dossier de logs s'il n'existe pas
mkdir -p "$LOG_DIR"

# Fonction de log
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Aller dans le répertoire du projet
cd "$PROJECT_DIR" || {
    log "❌ Erreur: Impossible d'accéder au répertoire $PROJECT_DIR"
    exit 1
}

# Vérifier que manage.py existe
if [ ! -f "$MANAGE_PY" ]; then
    log "❌ Erreur: manage.py non trouvé dans $PROJECT_DIR"
    exit 1
fi

# Récupérer les arguments
USER_ARG=""
BROKER_ARG="all"

if [ ! -z "$1" ]; then
    USER_ARG="--user $1"
fi

if [ ! -z "$2" ]; then
    BROKER_ARG="$2"
fi

# Lancer le refresh
log "🔄 Démarrage du refresh des tokens..."
log "📁 Répertoire: $PROJECT_DIR"
log "👤 Utilisateur: ${1:-'Tous'}"
log "🏦 Broker: $BROKER_ARG"

# Lancer la commande Django
if command -v python &> /dev/null; then
    # Python disponible directement
    python "$MANAGE_PY" refresh_broker_tokens --broker "$BROKER_ARG" $USER_ARG 2>&1 | tee -a "$LOG_FILE"
elif [ -f "$VENV_ACTIVATE" ]; then
    # Activer l'environnement virtuel et lancer
    source "$VENV_ACTIVATE" && python "$MANAGE_PY" refresh_broker_tokens --broker "$BROKER_ARG" $USER_ARG 2>&1 | tee -a "$LOG_FILE"
else
    # Essayer avec python3
    python3 "$MANAGE_PY" refresh_broker_tokens --broker "$BROKER_ARG" $USER_ARG 2>&1 | tee -a "$LOG_FILE"
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "✅ Refresh des tokens terminé avec succès"
else
    log "❌ Erreur lors du refresh des tokens (code: $EXIT_CODE)"
fi

# Nettoyer les anciens logs (garder 7 jours)
find "$LOG_DIR" -name "refresh_tokens_*.log" -mtime +7 -delete 2>/dev/null

exit $EXIT_CODE
