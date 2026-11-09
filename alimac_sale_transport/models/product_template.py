# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_transport = fields.Boolean(
        string='Is Transport',
        help='Check this if this product represents transport costs',
        default=False,
    )
