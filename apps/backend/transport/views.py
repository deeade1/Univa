from django.shortcuts import render

# Create your views here.
"""
Monitoring endpoints for dispatch system
"""
from django.http import JsonResponse
from django.views import View
from transport.services.dispatch.health import get_dispatch_health

class DispatchHealthView(View):
    """View for checking dispatch system health"""
    
    def get(self, request):
        health_status = get_dispatch_health()
        return JsonResponse({
            'status': 'healthy' if health_status.get('database') and health_status.get('cache') else 'unhealthy',
            'details': health_status,
            'available_modes': health_status.get('available_modes', []),
            'timestamp': health_status.get('timestamp')
        })

class DispatchMetricsView(View):
    """View for dispatch system metrics"""
    
    def get(self, request):
        from django.core.cache import cache
        from datetime import datetime
        
        metrics = {
            'current_mode': cache.get('dispatch_current_mode', 'simple'),
            'last_mode_switch': cache.get('dispatch_last_switch', None),
            'total_dispatches': cache.get('dispatch_total_count', 0),
            'successful_dispatches': cache.get('dispatch_success_count', 0),
            'fallback_count': cache.get('dispatch_fallback_count', 0),
            'ai_optimizations': cache.get('dispatch_ai_count', 0),
            'timestamp': datetime.now().isoformat(),
        }
        
        # Calculate success rate
        total = metrics['total_dispatches']
        successful = metrics['successful_dispatches']
        if total > 0:
            metrics['success_rate'] = (successful / total) * 100
        else:
            metrics['success_rate'] = 0
        
        return JsonResponse(metrics)