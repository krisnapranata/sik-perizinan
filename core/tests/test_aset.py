import os
import tempfile

from django.template import Context, Template
from django.test import SimpleTestCase, override_settings

from core.templatetags import aset


class TagAset(SimpleTestCase):
    def setUp(self):
        aset._cache.clear()

    def test_css_mendapat_versi_hash_isi(self):
        html = Template("{% load aset %}{% aset 'css/sik.css' %}").render(Context())
        self.assertRegex(html, r"^/static/css/sik\.css\?v=[0-9a-f]{10}$")

    def test_berkas_tidak_ada_tanpa_versi(self):
        self.assertEqual(aset.aset("css/tidak-ada.css"), "/static/css/tidak-ada.css")

    def test_versi_berganti_bila_isi_berubah(self):
        with tempfile.TemporaryDirectory() as d:
            jalur = os.path.join(d, "uji.js")
            with open(jalur, "w") as f:
                f.write("a")
            with override_settings(STATICFILES_DIRS=[d], DEBUG=True):
                pertama = aset.aset("uji.js")
                with open(jalur, "w") as f:
                    f.write("b")
                self.assertNotEqual(pertama, aset.aset("uji.js"))
