#  Copyright 2023 Simone Rubino - Aion Tech
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_compare


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    uom_id = fields.Many2one(
        string="UoM",
        comodel_name="uom.uom",
        compute="_compute_uom_id",
        store=True,
        readonly=False,
    )
    uom_min_quantity = fields.Float(
        string="Min. Quantity in UoM",
        digits="Product Unit",
        compute="_compute_uom_min_quantity",
        store=True,
        readonly=False,
    )

    def _is_applicable_for(self, product, qty_in_product_uom):
        """Override to check UoM compatibility.

        In Odoo 19, ``_is_applicable_for`` receives only ``(product, qty)``
        without a UoM argument.  The target UoM is passed via context key
        ``_pricelist_target_uom`` set by our ``ProductPricelist._compute_price_rule``
        override.

        When a pricelist item has a specific UoM set, it should only apply
        when the order line uses the same UoM.
        """
        res = super()._is_applicable_for(product, qty_in_product_uom)

        if res and self.uom_id:
            target_uom = self.env.context.get('_pricelist_target_uom')
            if target_uom and self.uom_id != target_uom:
                res = False

        return res

    @api.depends(
        "product_id",
        "product_tmpl_id",
    )
    def _compute_uom_id(self):
        for item in self:
            product = item.product_id or item.product_tmpl_id
            product_uom = product.uom_id
            if item.uom_id != product_uom:
                item.uom_id = product_uom

    def _sync_uom_min_quantity(
        self, source_quantity, source_uom, target_uom, target_qty_field
    ):
        """Convert `source_quantity` (in `source_uom`) to `target_uom`.
        Assign the result to field `self.target_qty_field`, if different."""
        self.ensure_one()
        if target_uom != source_uom:
            expected_target_quantity = source_uom._compute_quantity(
                source_quantity,
                target_uom,
                raise_if_failure=False,
                round=False,
            )
        else:
            expected_target_quantity = source_quantity

        # Assign only if different,
        # according to the precision of target field
        all_digits, precision_digits = self.fields_get(
            allfields=[
                target_qty_field,
            ],
            attributes=[
                "digits",
            ],
        )[target_qty_field]["digits"]
        if float_compare(
            self[target_qty_field],
            expected_target_quantity,
            precision_digits=precision_digits,
        ):
            self[target_qty_field] = expected_target_quantity

    @api.onchange(
        "product_id",
        "product_tmpl_id",
        "uom_id",
        "uom_min_quantity",
    )
    def onchange_uom_min_quantity(self):
        for item in self:
            product = item.product_id or item.product_tmpl_id
            product_uom = product.uom_id
            item._sync_uom_min_quantity(
                item.uom_min_quantity,
                item.uom_id,
                product_uom,
                "min_quantity",
            )

    @api.depends(
        "product_id",
        "product_tmpl_id",
        "min_quantity",
    )
    def _compute_uom_min_quantity(self):
        for item in self:
            product = item.product_id or item.product_tmpl_id
            product_uom = product.uom_id
            item._sync_uom_min_quantity(
                item.min_quantity,
                product_uom,
                item.uom_id,
                "uom_min_quantity",
            )
