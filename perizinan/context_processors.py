def navigasi(request):
    """Jumlah antrean untuk lencana di sidebar petugas dan instansi teknis."""
    hasil = {}
    pengguna = getattr(request, "user", None)
    if pengguna is None or not pengguna.is_authenticated or not pengguna.pemeriksa:
        return hasil
    from perizinan.services import antrean

    return hasil | {"jumlah_antrean": antrean(pengguna).count()}
