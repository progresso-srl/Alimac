#  Copyright 2023 Simone Rubino - Aion Tech
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(
        self,
        products,
        quantity,
        currency=None,
        uom=None,
        date=False,
        **kwargs,
    ):
        """Override to pass the target UoM through context so that
        ``ProductPricelistItem._is_applicable_for`` can filter by UoM.

        In Odoo 19, ``_is_applicable_for`` only receives ``(product, qty)``
        without the UoM.  We propagate it via context because the call chain
        ``_compute_price_rule → _get_applicable_rules → _is_applicable_for``
        does not forward the ``uom`` argument.
        """
        self_ctx = self.with_context(_pricelist_target_uom=uom)
        return super(ProductPricelist, self_ctx)._compute_price_rule(
            products,
            quantity,
            currency=currency,
            uom=uom,
            date=date,
            **kwargs,
        )
