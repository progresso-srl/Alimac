#  Copyright 2023 Simone Rubino - Aion Tech
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from math import log10

from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestProductPricelistItem(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.g_uom = cls.env.ref("uom.product_uom_gram")
        cls.kg_uom = cls.env.ref("uom.product_uom_kgm")

        # Converting g to kg needs to increase accuracy
        cls.uom_accuracy = cls.env.ref("uom.decimal_product_uom")
        cls.uom_accuracy.digits = log10(cls.kg_uom.factor)

        # UoM group needed to see UoM field
        cls.env.user.group_ids += cls.env.ref("uom.group_uom")
        product_1000_kg_form = Form(cls.env["product.product"])
        product_1000_kg_form.name = "Test product"
        product_1000_kg_form.uom_id = cls.kg_uom
        product_1000_kg_form.lst_price = 1000
        cls.product_1000_kg = product_1000_kg_form.save()

        # Activate advanced pricelist to apply surcharge
        cls.env.user.group_ids += cls.env.ref("product.group_product_pricelist")
        pricelist_g_kg_form = Form(cls.env["product.pricelist"])
        pricelist_g_kg_form.name = "Test pricelist"
        with pricelist_g_kg_form.item_ids.new() as item:
            item.product_tmpl_id = cls.product_1000_kg.product_tmpl_id
            item.compute_price = "formula"
            item.price_surcharge = 500
            item.uom_id = cls.g_uom
            item.uom_min_quantity = 1
        with pricelist_g_kg_form.item_ids.new() as item:
            item.product_tmpl_id = cls.product_1000_kg.product_tmpl_id
            item.compute_price = "formula"
            item.uom_id = cls.kg_uom
            item.uom_min_quantity = 1
        cls.pricelist_g_kg = pricelist_g_kg_form.save()

    def test_sync_uom_min_quantity(self):
        g_uom = self.g_uom
        kg_uom = self.kg_uom
        pricelist = self.pricelist_g_kg
        pricelist_form = Form(pricelist)
        with pricelist_form.item_ids.edit(0) as item:
            self.assertEqual(item.uom_id, kg_uom)
            self.assertEqual(item.min_quantity, 1)
            self.assertEqual(item.uom_min_quantity, 1)

            item.uom_id = g_uom
            self.assertEqual(item.min_quantity, 0.001)
            self.assertEqual(item.uom_min_quantity, 1)

            item.min_quantity = 1
            self.assertEqual(item.uom_min_quantity, 1000)

            item.uom_min_quantity = 1
            self.assertEqual(item.min_quantity, 0.001)

    def test_product_price(self):
        g_uom = self.g_uom
        kg_uom = self.kg_uom
        product = self.product_1000_kg
        pricelist = self.pricelist_g_kg

        g_price, g_rule = pricelist._compute_price_rule(
            product,
            1,
            uom=g_uom,
        )[product.id]
        kg_price, kg_rule = pricelist._compute_price_rule(
            product,
            1,
            uom=kg_uom,
        )[product.id]

        self.assertEqual(g_price, 1.5)
        self.assertEqual(kg_price, 1000)

    def test_product_price_with_uom_specific_rules(self):
        """Test that different UoM rules apply the correct price.
        
        When a pricelist has multiple rules with different UoMs,
        the system should apply the rule matching the order line UoM.
        """
        g_uom = self.g_uom
        kg_uom = self.kg_uom
        product = self.product_1000_kg
        pricelist = self.pricelist_g_kg

        # Get the rules from the pricelist
        g_rule_rec = pricelist.item_ids.filtered(lambda r: r.uom_id == g_uom)
        kg_rule_rec = pricelist.item_ids.filtered(lambda r: r.uom_id == kg_uom)

        # Verify rules are correctly configured with different UoMs
        self.assertTrue(g_rule_rec, "Should have a rule for grams")
        self.assertTrue(kg_rule_rec, "Should have a rule for kg")
        self.assertEqual(g_rule_rec.uom_id, g_uom)
        self.assertEqual(kg_rule_rec.uom_id, kg_uom)

        # When ordering in grams, the gram rule should apply
        g_price, g_rule_id = pricelist._compute_price_rule(
            product,
            1,
            uom=g_uom,
        )[product.id]
        self.assertEqual(g_rule_id, g_rule_rec.id, 
                        "When ordering in grams, the gram rule should be applied")
        self.assertEqual(g_price, 1.5, 
                        "Price should be 1.5 (base 1 + surcharge 0.5) for grams")

        # When ordering in kg, the kg rule should apply
        kg_price, kg_rule_id = pricelist._compute_price_rule(
            product,
            1,
            uom=kg_uom,
        )[product.id]
        self.assertEqual(kg_rule_id, kg_rule_rec.id,
                        "When ordering in kg, the kg rule should be applied")
        self.assertEqual(kg_price, 1000,
                        "Price should be 1000 (base price) for kg")
