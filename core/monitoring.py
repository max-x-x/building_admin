import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .services_config import SERVICES_CONFIG
from .models import ServiceStatusLog

@csrf_exempt
@require_http_methods(["POST"])
def check_services_status(request):
    results = []
    
    for service in SERVICES_CONFIG:
        try:
            response = requests.get(f"{service['url']}/ping", timeout=5)
            is_working = response.status_code == 200
            message = "Работает" if is_working else f"Ошибка: {response.status_code}"
            status_code = response.status_code
        except requests.exceptions.RequestException as e:
            is_working = False
            message = "Недоступен"
            status_code = None
        
        results.append({
            "name": service["name"],
            "icon": service["icon"],
            "is_working": is_working,
            "message": message
        })
        try:
            ServiceStatusLog.objects.create(
                service_name=service["name"],
                url=f"{service['url']}/ping",
                is_working=is_working,
                status_code=status_code,
                message=message
            )
        except Exception:
            pass
    
    return JsonResponse({"services": results})
