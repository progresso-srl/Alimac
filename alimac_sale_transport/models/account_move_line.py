# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Fields for material and transport tracking
    material_price_unit = fields.Float(
        string='Material Price Unit',
        digits='Product Price',
        help='Price per unit excluding transport',
        default=0.0,
        copy=True,
    )

    transport_price_unit = fields.Float(
        string='Transport Price Unit',
        digits='Product Price',
        help='Transport quota per unit',
        default=0.0,
        copy=True,
    )

    # Computed amounts (stored for reporting)
    material_amount = fields.Monetary(
        string='Material Amount',
        compute='_compute_material_transport_amounts',
        store=True,
        currency_field='currency_id',
        help='Material amount net of discount: material_price_unit × qty × (1 - discount%)',
    )

    transport_amount = fields.Monetary(
        string='Transport Amount',
        compute='_compute_material_transport_amounts',
        store=True,
        currency_field='currency_id',
        help='Transport amount: price_subtotal - material_amount',
    )

    @api.depends('quantity', 'discount', 'material_price_unit', 
                 'transport_price_unit', 'price_subtotal')
    def _compute_material_transport_amounts(self):
        """
        Compute material and transport amounts
        material_amount = material_price_unit × quantity × (1 - discount)
        transport_amount = price_subtotal - material_amount
        
        For credit notes, amounts will be negative (consistent with price_subtotal)
        """
        for line in self:
            if line.material_price_unit:
                # Calculate material amount with discount applied
                discount_factor = 1 - (line.discount / 100.0)
                line.material_amount = line.material_price_unit * line.quantity * discount_factor
                
                # Transport is the difference
                line.transport_amount = line.price_subtotal - line.material_amount
            else:
                # If no material price is set, everything is material (not incorporated)
                line.material_amount = line.price_subtotal
                line.transport_amount = 0.0
