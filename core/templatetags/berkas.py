from django import template

from core.berkas import jenis_pratinjau as _jenis

register = template.Library()


@register.filter
def jenis_pratinjau(berkas):
    return _jenis(berkas) if berkas else ""
