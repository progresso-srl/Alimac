# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon

from ..hooks import _migrate_gamma_code


@tagged("post_install", "-at_install")
class TestMigrazioneStudio(BaseCommon):
    def test_codice_gamma_da_studio(self):
        cr = self.env.cr
        # colonne come le crea Studio (annullate a fine test)
        cr.execute("ALTER TABLE product_template ADD COLUMN IF NOT EXISTS x_studio_codice_gamma varchar")
        cr.execute("ALTER TABLE product_product ADD COLUMN IF NOT EXISTS x_studio_codice_gamma_1 varchar")

        attr = self.env["product.attribute"].create(
            {"name": "Lavorazione", "value_ids": [(0, 0, {"name": "A"}), (0, 0, {"name": "B"})]}
        )
        unica = self.env["product.template"].create({"name": "Unica"})
        con_sku = self.env["product.template"].create({"name": "Con sku"})
        multi = self.env["product.template"].create(
            {
                "name": "Multi",
                "attribute_line_ids": [(0, 0, {"attribute_id": attr.id, "value_ids": [(6, 0, attr.value_ids.ids)]})],
            }
        )
        self.env.flush_all()
        cr.execute(
            "UPDATE product_template SET x_studio_codice_gamma = 'T-' || id WHERE id IN %s",
            ((unica | con_sku | multi)._ids,),
        )
        cr.execute(
            "UPDATE product_product SET x_studio_codice_gamma_1 = ' SKU-' || id || ' ' WHERE id IN %s",
            ((con_sku.product_variant_ids | multi.product_variant_ids[0])._ids,),
        )

        _migrate_gamma_code(self.env)

        # variante unica senza sku: prende il codice del modello
        self.assertEqual(unica.alimac_gamma_code, f"T-{unica.id}")
        # lo sku della variante vince sul codice del modello (spazi tolti)
        self.assertEqual(con_sku.alimac_gamma_code, f"SKU-{con_sku.product_variant_ids.id}")
        # più varianti: solo lo sku, il codice del modello non si propaga
        v1, v2 = multi.product_variant_ids
        self.assertEqual(v1.alimac_gamma_code, f"SKU-{v1.id}")
        self.assertFalse(v2.alimac_gamma_code)
        # idempotente
        _migrate_gamma_code(self.env)
        self.assertEqual(v1.alimac_gamma_code, f"SKU-{v1.id}")
