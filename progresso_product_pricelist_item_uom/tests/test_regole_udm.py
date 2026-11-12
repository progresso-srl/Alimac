# Copyright 2026 Progresso srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestRegoleUdm(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.g = cls.env.ref("uom.product_uom_gram")
        cls.kg = cls.env.ref("uom.product_uom_kgm")
        cls.t = cls.env.ref("uom.product_uom_ton")
        cls.prodotto = cls.env["product.product"].create(
            {"name": "Inerte prova", "uom_id": cls.kg.id, "lst_price": 1000}
        )
        cls.listino = cls.env["product.pricelist"].create({"name": "Listino UdM"})
        Regola = cls.env["product.pricelist.item"]
        base = {
            "pricelist_id": cls.listino.id,
            "applied_on": "1_product",
            "product_tmpl_id": cls.prodotto.product_tmpl_id.id,
            "compute_price": "fixed",
        }
        # prezzi espressi nell'UdM del prodotto (kg), come in Odoo e in OCA
        cls.regola_kg = Regola.create(
            dict(base, uom_id=cls.kg.id, min_quantity=1, fixed_price=900)
        )
        cls.regola_g = Regola.create(
            dict(base, uom_id=cls.g.id, min_quantity=0.001, fixed_price=1500)
        )

    def _regola(self, qty, uom):
        return self.listino._compute_price_rule(self.prodotto, qty, uom=uom)[
            self.prodotto.id
        ]

    def test_riga_in_kg_usa_regola_kg(self):
        prezzo, regola = self._regola(1, self.kg)
        self.assertEqual(regola, self.regola_kg.id)
        self.assertEqual(prezzo, 900)

    def test_riga_in_g_usa_regola_g_anche_sopra_il_minimo_kg(self):
        prezzo, regola = self._regola(2000, self.g)
        self.assertEqual(regola, self.regola_g.id)
        self.assertAlmostEqual(prezzo, 1.5)

    def test_regola_g_non_vale_per_kg(self):
        # 0,5 kg: sotto il minimo della regola kg, la regola g non deve scattare
        prezzo, regola = self._regola(0.5, self.kg)
        self.assertFalse(regola)
        self.assertEqual(prezzo, 1000)

    def test_udm_senza_regola_usa_quella_del_prodotto(self):
        prezzo, regola = self._regola(1, self.t)
        self.assertEqual(regola, self.regola_kg.id)
        self.assertAlmostEqual(prezzo, 900000)

    def test_senza_udm_vale_quella_del_prodotto(self):
        prezzo, regola = self._regola(1, None)
        self.assertEqual(regola, self.regola_kg.id)

    def test_riga_ordine_di_vendita(self):
        partner = self.env["res.partner"].create({"name": "Cliente prova"})
        ordine = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "pricelist_id": self.listino.id,
                "order_line": [
                    (0, 0, {"product_id": self.prodotto.id, "product_uom_qty": 2000,
                            "product_uom_id": self.g.id}),
                    (0, 0, {"product_id": self.prodotto.id, "product_uom_qty": 2,
                            "product_uom_id": self.kg.id}),
                ],
            }
        ) if "sale.order" in self.env else None
        if not ordine:
            self.skipTest("sale non installato")
        riga_g, riga_kg = ordine.order_line
        self.assertAlmostEqual(riga_g.price_unit, 1.5)
        self.assertEqual(riga_kg.price_unit, 900)
