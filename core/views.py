from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from core.admin import admin_sistem


@never_cache
def sehat(request):
    """Dipakai healthcheck Docker. Tidak membocorkan detail."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "gagal"}, status=503)
    return JsonResponse({"status": "ok"})


@login_required
def panduan(request):
    """Panduan fitur untuk presentasi dan serah terima. Hanya Admin Sistem."""
    if not admin_sistem(request):
        raise PermissionDenied
    return render(request, "core/panduan.html")
