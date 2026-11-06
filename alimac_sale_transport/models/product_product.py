# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_transport = fields.Boolean(
        string='Is Transport',
        help='Check this if this product represents transport costs',
        default=False,
    )
