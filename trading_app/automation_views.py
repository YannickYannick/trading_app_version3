from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
from .automation_service import AutomationService

@login_required
@csrf_exempt
def automation_status(request):
    """Récupère le statut de l'automatisation"""
    try:
        automation_service = AutomationService(request.user)
        status = automation_service.get_status()
        
        return JsonResponse({
            'success': True,
            'status': status
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_exempt
def start_automation(request):
    """Démarre l'automatisation"""
    try:
        automation_service = AutomationService(request.user)
        automation_service.start_automation()
        
        return JsonResponse({
            'success': True,
            'message': 'Automatisation démarrée avec succès'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_exempt
def stop_automation(request):
    """Arrête l'automatisation"""
    try:
        automation_service = AutomationService(request.user)
        automation_service.stop_automation()
        
        return JsonResponse({
            'success': True,
            'message': 'Automatisation arrêtée avec succès'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_exempt
def pause_automation(request):
    """Met en pause l'automatisation"""
    try:
        automation_service = AutomationService(request.user)
        automation_service.pause_automation()
        
        return JsonResponse({
            'success': True,
            'message': 'Automatisation mise en pause'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_exempt
def resume_automation(request):
    """Reprend l'automatisation"""
    try:
        automation_service = AutomationService(request.user)
        automation_service.resume_automation()
        
        return JsonResponse({
            'success': True,
            'message': 'Automatisation reprise'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_exempt
def update_frequency(request):
    """Met à jour la fréquence d'exécution"""
    try:
        data = json.loads(request.body)
        frequency_minutes = data.get('frequency_minutes', 30)
        
        if frequency_minutes < 1 or frequency_minutes > 1440:  # Entre 1 min et 24h
            return JsonResponse({
                'success': False,
                'error': 'Fréquence doit être entre 1 et 1440 minutes'
            })
        
        automation_service = AutomationService(request.user)
        automation_service.update_frequency(frequency_minutes)
        
        return JsonResponse({
            'success': True,
            'message': f'Fréquence mise à jour: {frequency_minutes} minutes'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_exempt
def execute_manual_cycle(request):
    """Exécute manuellement un cycle d'automatisation"""
    try:
        automation_service = AutomationService(request.user)
        results = automation_service.execute_automation_cycle()
        
        return JsonResponse({
            'success': True,
            'results': results,
            'message': 'Cycle d\'automatisation exécuté manuellement'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def automation_logs(request):
    """Récupère l'historique des exécutions"""
    try:
        from .models import AutomationExecutionLog
        
        logs = AutomationExecutionLog.objects.filter(
            user=request.user
        ).order_by('-execution_time')[:50]  # 50 derniers logs
        
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                'id': log.id,
                'execution_time': log.execution_time.isoformat(),
                'status': log.status,
                'summary': log.summary,
                'api_responses': log.api_responses,
                'errors': log.errors,
                'execution_duration': str(log.execution_duration) if log.execution_duration else None
            })
        
        return JsonResponse({
            'success': True,
            'logs': formatted_logs,
            'count': len(formatted_logs)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
