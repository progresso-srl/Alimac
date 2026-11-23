# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestTonnellate(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.t = cls.env.ref("uom.product_uom_ton")
        cls.kg = cls.env.ref("uom.product_uom_kgm")
        cls.unit = cls.env.ref("uom.product_uom_unit")
        Uom = cls.env["uom.uom"]
        # imballi come in Alimac: Sacco in kg, Pallet multiplo del sacco
        cls.sacco25 = Uom.create({"name": "Sacco 25kg", "relative_factor": 25, "relative_uom_id": cls.kg.id})
        cls.pallet = Uom.create({"name": "Pallet 60x25", "relative_factor": 60, "relative_uom_id": cls.sacco25.id})
        cls.ciottolo = cls.env["product.product"].create(
            {"name": "Ciottolo", "is_storable": True, "uom_id": cls.t.id, "uom_ids": [(6, 0, (cls.sacco25 | cls.pallet).ids)]}
        )
        # prodotto a pezzi con peso (kg)
        cls.pezzo = cls.env["product.product"].create({"name": "Pezzo", "uom_id": cls.unit.id, "weight": 40.0})
        cls.trasporto = cls.env["product.product"].create({"name": "Trasporto", "type": "service", "uom_id": cls.t.id})
        cls.customer = cls.env["res.partner"].create({"name": "Cliente"})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)

    # ------------------------------------------------------------------
    # Regola unica
    # ------------------------------------------------------------------

    def test_regola_tonnellate(self):
        p = self.ciottolo
        self.assertAlmostEqual(p._alimac_get_tons(12.5), 12.5)
        self.assertAlmostEqual(p._alimac_get_tons(2500, self.kg), 2.5)
        self.assertAlmostEqual(p._alimac_get_tons(80, self.sacco25), 2.0)
        self.assertAlmostEqual(p._alimac_get_tons(2, self.pallet), 3.0)
        # UdM non di peso: peso x quantità
        self.assertAlmostEqual(self.pezzo._alimac_get_tons(50), 2.0)
        self.pezzo.weight = 0
        self.assertEqual(self.pezzo._alimac_get_tons(50), 0.0)

    # ------------------------------------------------------------------
    # Ordine di vendita
    # ------------------------------------------------------------------

    def _order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (0, 0, {"product_id": self.ciottolo.id, "product_uom_qty": 2, "product_uom_id": self.pallet.id}),
                    (0, 0, {"product_id": self.ciottolo.id, "product_uom_qty": 10, "product_uom_id": self.sacco25.id}),
                    (0, 0, {"product_id": self.ciottolo.id, "product_uom_qty": 4.2}),
                    (0, 0, {"display_type": "line_note", "name": "nota"}),
                    # servizio in t (come la riga trasporto): non va sommato
                    (0, 0, {"product_id": self.trasporto.id, "product_uom_qty": 7.45, "price_unit": 10}),
                ],
            }
        )

    def test_ordine(self):
        order = self._order()
        lines = order.order_line
        self.assertEqual(
            [round(v, 3) for v in lines.mapped("alimac_qty_tons")], [3.0, 0.25, 4.2, 0.0, 0.0]
        )
        self.assertAlmostEqual(order.alimac_total_tons, 7.45)
        lines[0].product_uom_qty = 3
        self.assertAlmostEqual(order.alimac_total_tons, 8.95)

    def test_ordine_da_form(self):
        with Form(self.env["sale.order"]) as f:
            f.partner_id = self.customer
            with f.order_line.new() as line:
                line.product_id = self.ciottolo
                line.product_uom_qty = 1.5
            with f.order_line.new() as line:
                line.product_id = self.pezzo
                line.product_uom_qty = 25
            self.assertAlmostEqual(f.alimac_total_tons, 2.5)

    # ------------------------------------------------------------------
    # Trasferimento
    # ------------------------------------------------------------------

    def test_trasferimento(self):
        self.env["stock.quant"]._update_available_quantity(self.ciottolo, self.warehouse.lot_stock_id, 100)
        order = self._order()
        order.action_confirm()
        picking = order.picking_ids
        self.assertEqual(len(picking), 1)
        # domanda
        self.assertAlmostEqual(picking.alimac_tons, 7.45)
        # pesato: quantità effettiva diversa dalla domanda, senza backorder
        # Odoo 19 crea i movimenti nell'UdM del prodotto (t): 3 + 0,25 + 4,2
        self.assertEqual(picking.move_ids.product_uom, self.t)
        move = picking.move_ids.filtered(lambda m: m.product_uom_qty == 4.2)
        move.quantity = 4.0
        picking.move_ids.picked = True
        self.assertAlmostEqual(picking.alimac_tons, 7.25)
        picking.with_context(cancel_backorder=True)._action_done()
        self.assertEqual(picking.state, "done")
        self.assertAlmostEqual(picking.alimac_tons, 7.25)

    # ------------------------------------------------------------------
    # Stampa ordine
    # ------------------------------------------------------------------

    def test_stampa_ordine(self):
        order = self._order()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "sale.action_report_saleorder", order.ids
        )[0].decode()
        self.assertIn('name="alimac_total_tons"', html)
        # 7.450 / 7,450 secondo la lingua del cliente
        self.assertRegex(html, r"7[.,]450</span> t")
