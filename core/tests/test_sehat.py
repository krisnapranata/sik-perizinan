from django.test import TestCase


class Sehat(TestCase):
    def test_ok_tanpa_login(self):
        r = self.client.get("/sehat/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})
