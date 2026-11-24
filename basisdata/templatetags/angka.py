from django import template

register = template.Library()


@register.filter
def ribuan(n):
    """1234567 -> 1.234.567"""
    try:
        return f"{int(n or 0):,}".replace(",", ".")
    except (TypeError, ValueError):
        return n


@register.filter
def rupiah(n):
    return "Rp" + ribuan(n)


@register.filter
def rupiah_ringkas(n):
    """Untuk kartu KPI: 1.250.000.000 -> Rp1,25 M"""
    n = int(n or 0)
    for batas, akhiran in ((10**12, "T"), (10**9, "M"), (10**6, "jt")):
        if n >= batas:
            return "Rp" + f"{n / batas:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " " + akhiran
    return rupiah(n)


@register.simple_tag
def persen(nilai, maks):
    try:
        return round(int(nilai) * 100 / int(maks)) if int(maks) else 0
    except (TypeError, ValueError):
        return 0
