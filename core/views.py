from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def sehat(request):
    """Dipakai healthcheck Docker. Tidak membocorkan detail."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "gagal"}, status=503)
    return JsonResponse({"status": "ok"})
