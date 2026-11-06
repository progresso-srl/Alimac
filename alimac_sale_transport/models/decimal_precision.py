# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def _update_decimal_precision(env):
    """
    Update Product Price decimal precision to at least 4 decimals
    This is needed for accurate transport distribution calculations
    """
    precision = env['decimal.precision'].search([('name', '=', 'Product Price')], limit=1)
    
    if precision and precision.digits < 4:
        precision.sudo().write({'digits': 4})
    elif not precision:
        # Create if doesn't exist
        env['decimal.precision'].sudo().create({
            'name': 'Product Price',
            'digits': 4,
        })


def post_init_hook(env):
    """Called after module installation"""
    _update_decimal_precision(env)
