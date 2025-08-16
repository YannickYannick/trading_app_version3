"""
Vues pour la configuration et le test de l'auto-refresh des tokens Saxo Bank
"""

import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import BrokerCredentials
from .management.commands.refresh_saxo_tokens import Command as RefreshCommand


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def toggle_auto_refresh(request, broker_id):
    """Activer/désactiver l'auto-refresh pour un broker"""
    try:
        broker = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        
        if broker.broker_type != 'saxo':
            return JsonResponse({
                "success": False,
                "error": "Cette fonction est réservée aux brokers Saxo Bank"
            })
        
        data = json.loads(request.body)
        enabled = data.get('enabled', False)
        
        broker.auto_refresh_enabled = enabled
        broker.save()
        
        status = "activé" if enabled else "désactivé"
        
        return JsonResponse({
            "success": True,
            "message": f"Auto-refresh {status} pour {broker.name}",
            "enabled": enabled
        })
        
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Broker non trouvé ou non autorisé"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de la configuration: {str(e)}"
        })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_frequency(request, broker_id):
    """Mettre à jour la fréquence d'auto-refresh pour un broker"""
    try:
        broker = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        
        if broker.broker_type != 'saxo':
            return JsonResponse({
                "success": False,
                "error": "Cette fonction est réservée aux brokers Saxo Bank"
            })
        
        data = json.loads(request.body)
        frequency = data.get('frequency', 45)
        
        # Validation de la fréquence (15-55 minutes)
        if not (15 <= frequency <= 55):
            return JsonResponse({
                "success": False,
                "error": "La fréquence doit être comprise entre 15 et 55 minutes"
            })
        
        broker.auto_refresh_frequency = frequency
        broker.save()
        
        return JsonResponse({
            "success": True,
            "message": f"Fréquence mise à jour: {frequency} minutes",
            "frequency": frequency
        })
        
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Broker non trouvé ou non autorisé"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de la mise à jour: {str(e)}"
        })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def test_auto_refresh(request, broker_id):
    """Tester l'auto-refresh pour un broker spécifique"""
    try:
        broker = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        
        if broker.broker_type != 'saxo':
            return JsonResponse({
                "success": False,
                "error": "Cette fonction est réservée aux brokers Saxo Bank"
            })
        
        if not broker.auto_refresh_enabled:
            return JsonResponse({
                "success": False,
                "error": "Auto-refresh non activé pour ce broker"
            })
        
        # Créer une instance de la commande et tester
        refresh_command = RefreshCommand()
        
        # Simuler le test avec --dry-run et --broker-id
        from io import StringIO
        from django.core.management import call_command
        
        # Capturer la sortie de la commande
        out = StringIO()
        call_command('refresh_saxo_tokens', 
                    broker_id=broker_id, 
                    dry_run=True, 
                    stdout=out)
        
        output = out.getvalue()
        
        return JsonResponse({
            "success": True,
            "message": "Test auto-refresh terminé avec succès",
            "output": output,
            "broker_name": broker.name,
            "frequency": broker.auto_refresh_frequency
        })
        
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Broker non trouvé ou non autorisé"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors du test: {str(e)}"
        })
