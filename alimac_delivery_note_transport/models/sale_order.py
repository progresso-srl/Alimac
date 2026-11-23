# -*- coding: utf-8 -*-

from odoo import api, fields, models

from .product_product import TONS_DIGITS


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    alimac_total_tons = fields.Float(
        string='Total Tonnage',
        compute='_compute_alimac_total_tons',
        store=True,
        digits=TONS_DIGITS,
        help='Sum of the tonnes of the goods lines.',
    )

    @api.depends('order_line.alimac_qty_tons')
    def _compute_alimac_total_tons(self):
        for order in self:
            order.alimac_total_tons = sum(order.order_line.mapped('alimac_qty_tons'))
