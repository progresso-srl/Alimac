# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestAlimacBase(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Cliente"})
        cls.product = cls.env["product.product"].create({"name": "Ciottolo"})

    # ------------------------------------------------------------------
    # Codice Gamma
    # ------------------------------------------------------------------

    def test_codice_gamma_variante_unica(self):
        tmpl = self.env["product.template"].create({"name": "Unica", "alimac_gamma_code": "G-001"})
        self.assertEqual(tmpl.product_variant_ids.alimac_gamma_code, "G-001")
        tmpl.alimac_gamma_code = "G-002"
        self.assertEqual(tmpl.product_variant_ids.alimac_gamma_code, "G-002")
        self.assertEqual(self.env["product.template"].search([("alimac_gamma_code", "=", "G-002")]), tmpl)

    def test_codice_gamma_piu_varianti(self):
        attr = self.env["product.attribute"].create(
            {"name": "Granulometria", "value_ids": [(0, 0, {"name": "10-20"}), (0, 0, {"name": "20-40"})]}
        )
        tmpl = self.env["product.template"].create(
            {
                "name": "Multi",
                "attribute_line_ids": [(0, 0, {"attribute_id": attr.id, "value_ids": [(6, 0, attr.value_ids.ids)]})],
            }
        )
        v1, v2 = tmpl.product_variant_ids
        v1.alimac_gamma_code = "A1"
        v2.alimac_gamma_code = "A2"
        self.assertFalse(tmpl.alimac_gamma_code)
        self.assertEqual(self.env["product.template"].search([("alimac_gamma_code", "=", "A2")]), tmpl)
        self.assertFalse(v1.copy().alimac_gamma_code)

    # ------------------------------------------------------------------
    # Contatto
    # ------------------------------------------------------------------

    def test_listino_cliente(self):
        self.env["product.customerinfo"].create(
            {"partner_id": self.customer.id, "product_tmpl_id": self.product.product_tmpl_id.id, "price": 50}
        )
        self.assertEqual(self.customer.alimac_customerinfo_count, 1)
        action = self.customer.action_alimac_open_customerinfo()
        self.assertEqual(self.env[action["res_model"]].search(action["domain"]).partner_id, self.customer)
