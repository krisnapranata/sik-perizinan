from core.audit import alamat_ip


class AlamatIPMiddleware:
    """Menyimpan IP klien untuk log audit. X-Real-IP selalu ditimpa oleh Nginx."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
        token = alamat_ip.set(ip)
        try:
            return self.get_response(request)
        finally:
            alamat_ip.reset(token)


class WajibGantiPasswordMiddleware:
    """Pengguna berpassword awal (hasil impor) hanya boleh membuka halaman ganti password."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.shortcuts import redirect
        from django.urls import reverse

        pengguna = getattr(request, "user", None)
        if pengguna is not None and pengguna.is_authenticated and pengguna.wajib_ganti_password:
            boleh = (
                reverse("akun:ganti_password"),
                reverse("akun:keluar"),
                reverse("sehat"),
                settings.STATIC_URL,
            )
            if not request.path.startswith(boleh):
                return redirect("akun:ganti_password")
        return self.get_response(request)
