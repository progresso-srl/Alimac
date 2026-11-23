# -*- coding: utf-8 -*-

from odoo import api, fields, models

from .product_product import TONS_DIGITS


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    alimac_qty_tons = fields.Float(
        string='Qty (t)',
        compute='_compute_alimac_qty_tons',
        store=True,
        digits=TONS_DIGITS,
        help='Ordered quantity in tonnes. Goods lines only: transport, '
             'services, down payments, sections and notes count as 0.',
    )

    def _alimac_is_goods_line(self):
        self.ensure_one()
        return bool(
            not self.display_type
            and not self.is_downpayment
            and self.product_id.type == 'consu'
        )

    @api.depends('product_id', 'product_uom_qty', 'product_uom_id', 'display_type', 'is_downpayment')
    def _compute_alimac_qty_tons(self):
        for line in self:
            if line._alimac_is_goods_line():
                line.alimac_qty_tons = line.product_id._alimac_get_tons(
                    line.product_uom_qty, line.product_uom_id
                )
            else:
                line.alimac_qty_tons = 0.0
