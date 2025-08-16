from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import BrokerCredentials
from .services import BrokerService
from datetime import datetime

@login_required
@csrf_exempt
def sync_saxo_complete(request, broker_id):
    """Synchronisation complète Saxo Bank avec affichage détaillé"""
    try:
        broker_creds = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        
        if broker_creds.broker_type != 'saxo':
            return JsonResponse({
                "success": False,
                "error": "Cette fonction est réservée aux brokers Saxo Bank"
            })
        
        print(f"🔄 Synchronisation complète Saxo Bank pour {broker_creds.name}")
        
        broker_service = BrokerService(request.user)
        results = {}
        
        # 1. Test de connectivité
        try:
            saxo_broker = broker_service.get_broker_instance(broker_creds)
            connectivity_results = saxo_broker.test_connectivity()
            results['connectivity'] = connectivity_results
            print("🔍 Tests de connectivité terminés")
        except Exception as e:
            results['connectivity'] = {
                'error': str(e),
                'message': f"Erreur lors des tests de connectivité: {str(e)}"
            }
            print(f"❌ Erreur tests de connectivité: {e}")
        
        # 2. Vérifier le statut du token
        try:
            token_status = saxo_broker.check_token_status()
            results['token_status'] = {
                'valid': token_status.get('valid', False),
                'expires_in': token_status.get('expires_in', 'N/A'),
                'message': token_status.get('message', 'Statut inconnu')
            }
            print(f"🔑 Token Saxo: {'✅ Valide' if token_status.get('valid') else '❌ Expiré'}")
        except Exception as e:
            results['token_status'] = {
                'valid': False,
                'error': str(e),
                'message': f"Erreur vérification token: {str(e)}"
            }
            print(f"❌ Erreur vérification token: {e}")
        
        # 2. Synchroniser les positions
        try:
            positions = broker_service.sync_positions_from_broker(broker_creds)
            results['positions'] = {
                'success': True,
                'count': len(positions),
                'message': f"{len(positions)} positions synchronisées",
                'details': [{
                    'symbol': pos.asset_tradable.symbol,
                    'size': float(pos.size),
                    'entry_price': float(pos.entry_price) if pos.entry_price else None,
                    'current_price': float(pos.current_price) if pos.current_price else None
                } for pos in positions[:10]]  # Limiter à 10 pour l'affichage
            }
            print(f"✅ Positions: {len(positions)} synchronisées")
        except Exception as e:
            results['positions'] = {
                'success': False,
                'error': str(e),
                'message': f"Erreur positions: {str(e)}"
            }
            print(f"❌ Erreur positions: {e}")
        
        # 3. Synchroniser les trades
        try:
            trades_result = broker_service.sync_trades_from_broker(broker_creds)
            if trades_result['success']:
                results['trades'] = {
                    'success': True,
                    'saved_count': trades_result['saved_count'],
                    'total_trades': trades_result['total_trades'],
                    'message': f"{trades_result['saved_count']} nouveaux trades synchronisés"
                }
                print(f"✅ Trades: {trades_result['saved_count']} nouveaux")
            else:
                results['trades'] = {
                    'success': False,
                    'error': trades_result['error'],
                    'message': f"Erreur trades: {trades_result['error']}"
                }
                print(f"❌ Erreur trades: {trades_result['error']}")
        except Exception as e:
            results['trades'] = {
                'success': False,
                'error': str(e),
                'message': f"Erreur trades: {str(e)}"
            }
            print(f"❌ Erreur trades: {e}")
        
        # 4. Synchroniser les ordres en cours
        try:
            orders_result = broker_service.sync_pending_orders_from_broker(broker_creds)
            if orders_result['success']:
                results['orders'] = {
                    'success': True,
                    'count': orders_result['count'],
                    'message': f"{orders_result['count']} ordres en cours synchronisés"
                }
                print(f"✅ Ordres: {orders_result['count']} synchronisés")
            else:
                results['orders'] = {
                    'success': False,
                    'error': orders_result['error'],
                    'message': f"Erreur ordres: {orders_result['error']}"
                }
                print(f"❌ Erreur ordres: {orders_result['error']}")
        except Exception as e:
            results['orders'] = {
                'success': False,
                'error': str(e),
                'message': f"Erreur ordres: {str(e)}"
            }
            print(f"❌ Erreur ordres: {e}")
        
        # 5. Récupérer le solde du compte
        try:
            balance = saxo_broker.get_account_balance()
            results['balance'] = {
                'success': True,
                'balance': balance,
                'message': f"Solde récupéré: {balance}"
            }
            print(f"💰 Solde: {balance}")
        except Exception as e:
            results['balance'] = {
                'success': False,
                'error': str(e),
                'message': f"Erreur récupération solde: {str(e)}"
            }
            print(f"❌ Erreur solde: {e}")
        
        return JsonResponse({
            "success": True,
            "message": "Synchronisation complète Saxo Bank terminée",
            "broker_name": broker_creds.name,
            "broker_type": broker_creds.broker_type,
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_operations": sum(1 for r in results.values() if r.get('success')),
                "total_errors": sum(1 for r in results.values() if not r.get('success')),
                "positions_count": results.get('positions', {}).get('count', 0),
                "trades_count": results.get('trades', {}).get('saved_count', 0),
                "orders_count": results.get('orders', {}).get('count', 0)
            }
        })
        
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Broker non trouvé ou non autorisé"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors de la synchronisation: {str(e)}"
        })

@login_required
@csrf_exempt
def force_refresh_saxo_tokens(request, broker_id):
    """Forcer le refresh des tokens Saxo Bank"""
    try:
        broker_creds = BrokerCredentials.objects.get(id=broker_id, user=request.user)
        
        if broker_creds.broker_type != 'saxo':
            return JsonResponse({
                "success": False,
                "error": "Cette fonction est réservée aux brokers Saxo Bank"
            })
        
        print(f"🔄 Refresh forcé des tokens Saxo Bank pour {broker_creds.name}")
        
        broker_service = BrokerService(request.user)
        saxo_broker = broker_service.get_broker_instance(broker_creds)
        
        # Vérifier le statut actuel
        current_status = saxo_broker.check_token_status()
        print(f"🔑 Statut actuel: {current_status}")
        
        # Tenter le refresh
        refresh_success = False
        if saxo_broker.refresh_token and saxo_broker.refresh_token != saxo_broker.access_token:
            print("🔄 Tentative de refresh du token...")
            refresh_success = saxo_broker.refresh_auth_token()
            
            if refresh_success:
                print("✅ Refresh réussi")
                # Récupérer le nouveau statut
                new_status = saxo_broker.check_token_status()
                
                return JsonResponse({
                    "success": True,
                    "message": "Tokens Saxo Bank rafraîchis avec succès",
                    "broker_name": broker_creds.name,
                    "previous_status": current_status,
                    "new_status": new_status,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": "Échec du refresh des tokens",
                    "broker_name": broker_creds.name,
                    "current_status": current_status
                })
        else:
            return JsonResponse({
                "success": False,
                "error": "Refresh token non disponible ou identique à l'access token (token 24h)",
                "broker_name": broker_creds.name,
                "current_status": current_status,
                "note": "Les tokens 24h de Saxo Bank ne peuvent pas être rafraîchis automatiquement"
            })
        
    except BrokerCredentials.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Broker non trouvé ou non autorisé"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Erreur lors du refresh des tokens: {str(e)}"
        })
