# Copyright 2026 Progresso srl
from datetime import date

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestReportMensile(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pf = cls.env.ref("l10n_it_delivery_note.transport_condition_PF")
        cls.pa = cls.env.ref("l10n_it_delivery_note.transport_condition_PA")
        P = cls.env["res.partner"]
        cls.vettore_a = P.create({"name": "Vettore A"})
        cls.vettore_b = P.create({"name": "Vettore B"})
        cls.milano = P.create({"name": "Cliente Milano", "city": "Milano"})
        cls.roma = P.create({"name": "Cliente Roma", "city": "Roma"})
        DN = cls.env["stock.delivery.note"]
        base = {"date": date(2026, 11, 10), "state": "done",
                "transport_condition_id": cls.pf.id}
        DN.create(dict(base, carrier_id=cls.vettore_a.id, partner_id=cls.milano.id, transport_cost=200))
        DN.create(dict(base, carrier_id=cls.vettore_a.id, partner_id=cls.milano.id, transport_cost=100))
        DN.create(dict(base, carrier_id=cls.vettore_b.id, partner_id=cls.roma.id, transport_cost=180))
        # esclusi: porto assegnato, bozza, senza vettore
        DN.create(dict(base, carrier_id=cls.vettore_b.id, partner_id=cls.roma.id,
                       transport_condition_id=cls.pa.id, transport_cost=999))
        DN.create(dict(base, carrier_id=cls.vettore_b.id, partner_id=cls.roma.id,
                       state="draft", transport_cost=999))
        DN.create(dict(base, partner_id=cls.roma.id, transport_cost=999))

    def _html(self, **vals):
        wiz = self.env["transport.report.wizard"].create(dict({"month": "11", "year": 2026}, **vals))
        action = wiz.with_context(discard_logo_check=True).action_print_report()
        # come il client web con `data`: nessun docid
        html = self.env["ir.actions.report"]._render_qweb_html(
            action["report_name"], None, data=action["data"])[0]
        return action["data"], html.decode()

    def test_dati_e_stampa(self):
        data, html = self._html()
        righe = {c["carrier_name"]: (c["total_trips"], c["total_cost"]) for c in data["report_data"]}
        self.assertEqual(righe, {"Vettore A": (2, 300.0), "Vettore B": (1, 180.0)})
        self.assertIn("Vettore A", html)
        self.assertIn("Milano", html)
        self.assertIn("480.00", html)

    def test_mese_vuoto(self):
        data, html = self._html(month="1")
        self.assertFalse(data["report_data"])
        self.assertIn("No transport data found", html)

    def test_un_vettore(self):
        data, html = self._html(carrier_id=self.vettore_a.id)
        self.assertEqual([c["carrier_name"] for c in data["report_data"]], ["Vettore A"])
