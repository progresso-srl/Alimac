# Copyright 2026 Progresso srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestPrezziClienteUdm(BaseCommon):
    """Caso Longobardi: stesso prodotto, prezzo a tonnellata diverso per imballo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Udm = cls.env["uom.uom"]
        cls.t = cls.env.ref("uom.product_uom_ton")
        cls.pallet = Udm.create(
            {
                "name": "Pallet 1500kg - 60x25kg (test)",
                "relative_factor": 1.5,
                "relative_uom_id": cls.t.id,
            }
        )
        cls.bigbag_15 = Udm.create(
            {
                "name": "Big Bag 1500kg (test)",
                "relative_factor": 1.5,
                "relative_uom_id": cls.t.id,
            }
        )
        cls.bigbag_1 = Udm.create(
            {
                "name": "Big Bag 1000kg (test)",
                "relative_factor": 1.0,
                "relative_uom_id": cls.t.id,
            }
        )
        cls.sacco_25 = Udm.create(
            {
                "name": "Sacco 25kg (test)",
                "relative_factor": 0.025,
                "relative_uom_id": cls.t.id,
            }
        )
        cls.prodotto = cls.env["product.product"].create(
            {
                "name": "Ciottoli Bianco Carrara 15/25 (test)",
                "uom_id": cls.t.id,
                "list_price": 200.0,
                "taxes_id": [(5, 0, 0)],
            }
        )
        cls.cliente = cls.env["res.partner"].create({"name": "Longobardi (test)"})
        cls.altro_cliente = cls.env["res.partner"].create({"name": "Altro (test)"})
        cls.listino = cls.env["product.pricelist"].create(
            {
                "name": "Prezzi cliente (test)",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "3_global",
                            "compute_price": "formula",
                            "base": "partner",
                        },
                    )
                ],
            }
        )
        cls.cliente.property_product_pricelist = cls.listino
        cls.altro_cliente.property_product_pricelist = cls.listino
        # prezzi a tonnellata, come in scheda prodotto (inseriti dal più basso
        # al più alto per verificare che non vinca più il prezzo minore)
        for udm, prezzo in (
            (cls.bigbag_15, 65.0),
            (cls.bigbag_1, 85.0),
            (cls.pallet, 95.0),
        ):
            cls._riga_cliente(cls.cliente, udm, prezzo)

    @classmethod
    def _riga_cliente(cls, cliente, udm, prezzo):
        return cls.env["product.customerinfo"].create(
            {
                "partner_id": cliente.id,
                "product_tmpl_id": cls.prodotto.product_tmpl_id.id,
                "product_uom_id": udm.id,
                "price": prezzo,
            }
        )

    def _ordine(self, cliente, *udm):
        return self.env["sale.order"].create(
            {
                "partner_id": cliente.id,
                "pricelist_id": self.listino.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.prodotto.id,
                            "product_uom_qty": 1,
                            "product_uom_id": u.id,
                        },
                    )
                    for u in udm
                ],
            }
        )

    def test_prezzo_per_imballo(self):
        ordine = self._ordine(self.cliente, self.pallet, self.bigbag_15, self.bigbag_1)
        pallet, bigbag_15, bigbag_1 = ordine.order_line
        self.assertAlmostEqual(pallet.price_unit, 142.5)  # 95 €/t x 1,5 t
        self.assertAlmostEqual(bigbag_15.price_unit, 97.5)  # 65 €/t x 1,5 t
        self.assertAlmostEqual(bigbag_1.price_unit, 85.0)  # 85 €/t x 1 t

    def test_imballo_senza_riga_usa_riga_generica(self):
        self._riga_cliente(self.cliente, self.t, 70.0)
        ordine = self._ordine(self.cliente, self.sacco_25, self.t)
        sacco, sfuso = ordine.order_line
        self.assertAlmostEqual(sacco.price_unit, 1.75)  # 70 €/t x 0,025 t
        self.assertAlmostEqual(sfuso.price_unit, 70.0)

    def test_imballo_senza_riga_ne_generica_usa_prezzo_standard(self):
        # non deve prendere il prezzo di un altro imballo
        ordine = self._ordine(self.cliente, self.sacco_25)
        self.assertAlmostEqual(ordine.order_line.price_unit, 5.0)  # 200 €/t x 0,025

    def test_cliente_senza_prezzi_usa_prezzo_standard(self):
        ordine = self._ordine(self.altro_cliente, self.pallet)
        self.assertAlmostEqual(ordine.order_line.price_unit, 300.0)  # 200 x 1,5

    def test_riga_sulla_variante_prima_di_quella_sul_modello(self):
        self.env["product.customerinfo"].create(
            {
                "partner_id": self.cliente.id,
                "product_tmpl_id": self.prodotto.product_tmpl_id.id,
                "product_id": self.prodotto.id,
                "product_uom_id": self.pallet.id,
                "price": 99.0,
                "sequence": 100,
            }
        )
        ordine = self._ordine(self.cliente, self.pallet)
        self.assertAlmostEqual(ordine.order_line.price_unit, 148.5)  # 99 x 1,5

    def test_senza_udm_comportamento_oca(self):
        # senza UdM nel contesto resta la scelta del modulo OCA
        riga = self.prodotto._select_customerinfo(partner=self.cliente)
        self.assertEqual(riga.price, 65.0)
