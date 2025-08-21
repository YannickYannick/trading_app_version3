# Script PowerShell pour lancer le refresh des tokens depuis un cron
# Usage: .\refresh_tokens_cron.ps1 [user] [broker]

param(
    [string]$User = "",
    [string]$Broker = "all"
)

# Configuration
$ProjectDir = "C:\Users\Yannick-ConceptD\Documents\Projet - site trading\Trading_app_version3\trading_app_version3"
$VenvActivate = "$ProjectDir\venv\Scripts\Activate.ps1"
$ManagePy = "$ProjectDir\manage.py"

# Logs
$LogDir = "$ProjectDir\logs"
$LogFile = "$LogDir\refresh_tokens_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Créer le dossier de logs s'il n'existe pas
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Fonction de log
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "$Timestamp - $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

# Aller dans le répertoire du projet
try {
    Set-Location $ProjectDir
} catch {
    Write-Log "❌ Erreur: Impossible d'accéder au répertoire $ProjectDir"
    exit 1
}

# Vérifier que manage.py existe
if (!(Test-Path $ManagePy)) {
    Write-Log "❌ Erreur: manage.py non trouvé dans $ProjectDir"
    exit 1
}

# Construire la commande
$UserArg = ""
if ($User) {
    $UserArg = "--user $User"
}

Write-Log "🔄 Démarrage du refresh des tokens..."
Write-Log "📁 Répertoire: $ProjectDir"
Write-Log "👤 Utilisateur: $($User ? $User : 'Tous')"
Write-Log "🏦 Broker: $Broker"

# Lancer la commande Django
try {
    # Activer l'environnement virtuel et lancer
    if (Test-Path $VenvActivate) {
        Write-Log "🔧 Activation de l'environnement virtuel..."
        & $VenvActivate
        
        $Command = "python `"$ManagePy`" refresh_broker_tokens --broker $Broker $UserArg"
        Write-Log "🚀 Exécution: $Command"
        
        Invoke-Expression $Command 2>&1 | Tee-Object -FilePath $LogFile -Append
    } else {
        Write-Log "⚠️ Environnement virtuel non trouvé, tentative avec Python système..."
        $Command = "python `"$ManagePy`" refresh_broker_tokens --broker $Broker $UserArg"
        Write-Log "🚀 Exécution: $Command"
        
        Invoke-Expression $Command 2>&1 | Tee-Object -FilePath $LogFile -Append
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "✅ Refresh des tokens terminé avec succès"
    } else {
        Write-Log "❌ Erreur lors du refresh des tokens (code: $LASTEXITCODE)"
    }
    
} catch {
    Write-Log "❌ Erreur lors de l'exécution: $($_.Exception.Message)"
    exit 1
}

# Nettoyer les anciens logs (garder 7 jours)
try {
    $CutoffDate = (Get-Date).AddDays(-7)
    Get-ChildItem -Path $LogDir -Filter "refresh_tokens_*.log" | 
        Where-Object { $_.LastWriteTime -lt $CutoffDate } | 
        Remove-Item -Force
    
    Write-Log "🧹 Nettoyage des anciens logs terminé"
} catch {
    Write-Log "⚠️ Erreur lors du nettoyage des logs: $($_.Exception.Message)"
}

exit $LASTEXITCODE
