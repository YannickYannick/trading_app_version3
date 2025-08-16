"""
Vues pour la fonctionnalité PWA (Progressive Web App)
Gestion des notifications push, service worker, etc.
"""

import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Strategy, StrategyExecution, BrokerCredentials
from .telegram_notifications import telegram_notifier


@csrf_exempt
@require_http_methods(["POST"])
def subscribe_push_notifications(request):
    """S'abonner aux notifications push"""
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')
        user_id = data.get('user_id')
        
        if not subscription or not user_id:
            return JsonResponse({
                "success": False,
                "error": "Données d'abonnement manquantes"
            })
        
        # Ici vous pourriez sauvegarder l'abonnement en base
        # pour envoyer des notifications plus tard
        
        return JsonResponse({
            "success": True,
            "message": "Abonnement aux notifications réussi"
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de l'abonnement: {str(e)}"
        })


@csrf_exempt
@require_http_methods(["POST"])
def unsubscribe_push_notifications(request):
    """Se désabonner des notifications push"""
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')
        user_id = data.get('user_id')
        
        if not subscription or not user_id:
            return JsonResponse({
                "success": False,
                "error": "Données de désabonnement manquantes"
            })
        
        # Ici vous pourriez supprimer l'abonnement de la base
        
        return JsonResponse({
            "success": True,
            "message": "Désabonnement réussi"
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors du désabonnement: {str(e)}"
        })


@login_required
def pwa_status(request):
    """Obtenir le statut de la PWA pour l'utilisateur"""
    try:
        # Statistiques de l'utilisateur
        user_strategies = Strategy.objects.filter(user=request.user).count()
        active_strategies = Strategy.objects.filter(user=request.user, is_active=True).count()
        recent_executions = StrategyExecution.objects.filter(
            strategy__user=request.user
        ).order_by('-executed_at')[:5]
        
        # Brokers actifs
        active_brokers = BrokerCredentials.objects.filter(
            user=request.user, is_active=True
        ).count()
        
        # Dernières activités
        recent_activities = []
        for execution in recent_executions:
            recent_activities.append({
                'type': 'strategy_execution',
                'strategy_name': execution.strategy.name,
                'timestamp': execution.executed_at.isoformat(),
                'status': execution.status,
                'message': f"Stratégie {execution.strategy.name} exécutée"
            })
        
        return JsonResponse({
            "success": True,
            "data": {
                "user_stats": {
                    "total_strategies": user_strategies,
                    "active_strategies": active_strategies,
                    "active_brokers": active_brokers
                },
                "recent_activities": recent_activities,
                "pwa_version": "1.0.0",
                "last_updated": timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de la récupération du statut: {str(e)}"
        })


@csrf_exempt
@require_http_methods(["POST"])
def send_test_notification(request):
    """Envoyer une notification de test (pour le développement)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        message = data.get('message', 'Notification de test PWA')
        
        if not user_id:
            return JsonResponse({
                "success": False,
                "error": "ID utilisateur requis"
            })
        
        # Ici vous pourriez envoyer une vraie notification push
        # Pour l'instant, on utilise Telegram comme fallback
        
        try:
            telegram_notifier.send_order_notification(
                f"🧪 Test PWA: {message}\n"
                f"Utilisateur: {user_id}\n"
                f"Timestamp: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
        except Exception as telegram_error:
            print(f"Erreur Telegram: {telegram_error}")
        
        return JsonResponse({
            "success": True,
            "message": "Notification de test envoyée",
            "timestamp": timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de l'envoi: {str(e)}"
        })


@login_required
def pwa_manifest(request):
    """Retourner le manifeste PWA dynamique"""
    try:
        # Récupérer les informations de l'utilisateur
        user_strategies = Strategy.objects.filter(user=request.user).count()
        user_brokers = BrokerCredentials.objects.filter(user=request.user).count()
        
        manifest = {
            "name": f"Trading App - {request.user.username}",
            "short_name": "Trading App",
            "description": f"Application de trading avec {user_strategies} stratégies et {user_brokers} brokers",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#ffffff",
            "theme_color": "#007bff",
            "categories": ["finance", "business", "productivity"],
            "lang": "fr",
            "dir": "ltr",
            "icons": [
                {
                    "src": "/static/icons/icon-72x72.png",
                    "sizes": "72x72",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-96x96.png",
                    "sizes": "96x96",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-128x128.png",
                    "sizes": "128x128",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-144x144.png",
                    "sizes": "144x144",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-152x152.png",
                    "sizes": "152x152",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-384x384.png",
                    "sizes": "384x384",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ],
            "shortcuts": [
                {
                    "name": "Stratégies",
                    "short_name": "Stratégies",
                    "description": f"Gérer vos {user_strategies} stratégies de trading",
                    "url": "/strategies/tabulator/",
                    "icons": [
                        {
                            "src": "/static/icons/strategy-96x96.png",
                            "sizes": "96x96"
                        }
                    ]
                },
                {
                    "name": "Brokers",
                    "short_name": "Brokers",
                    "description": f"Gérer vos {user_brokers} brokers",
                    "url": "/brokers/",
                    "icons": [
                        {
                            "src": "/static/icons/broker-96x96.png",
                            "sizes": "96x96"
                        }
                    ]
                },
                {
                    "name": "Positions",
                    "short_name": "Positions",
                    "description": "Voir vos positions",
                    "url": "/positions/tabulator/",
                    "icons": [
                        {
                            "src": "/static/icons/position-96x96.png",
                            "sizes": "96x96"
                        }
                    ]
                }
            ]
        }
        
        response = HttpResponse(
            json.dumps(manifest, indent=2),
            content_type='application/json'
        )
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de la génération du manifeste: {str(e)}"
        })


@login_required
def pwa_offline(request):
    """Page hors ligne personnalisée pour l'utilisateur"""
    try:
        # Récupérer les informations de base de l'utilisateur
        user_strategies = Strategy.objects.filter(user=request.user).count()
        user_brokers = BrokerCredentials.objects.filter(user=request.user).count()
        
        context = {
            "user": request.user,
            "stats": {
                "strategies": user_strategies,
                "brokers": user_brokers
            }
        }
        
        # Utiliser le template offline.html
        from django.shortcuts import render
        return render(request, 'offline.html', context)
        
    except Exception as e:
        # Fallback en cas d'erreur
        return HttpResponse(
            f"""
            <html>
            <head><title>Hors ligne - Trading App</title></head>
            <body>
                <h1>Vous êtes hors ligne</h1>
                <p>Vérifiez votre connexion internet et réessayez.</p>
            </body>
            </html>
            """,
            content_type='text/html'
        )
