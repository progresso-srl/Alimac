# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Fields specific to transport line
    transport_reference_amount = fields.Monetary(
        string='Transport Reference Amount',
        currency_field='currency_id',
        help='Original transport amount when incorporated (shown on transport line only)',
        default=0.0,
        copy=True,
    )

    # Fields for all lines
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

    @api.depends('product_uom_qty', 'discount', 'material_price_unit', 
                 'transport_price_unit', 'price_subtotal')
    def _compute_material_transport_amounts(self):
        """
        Compute material and transport amounts
        material_amount = material_price_unit × quantity × (1 - discount)
        transport_amount = price_subtotal - material_amount
        """
        for line in self:
            if line.material_price_unit:
                # Calculate material amount with discount applied
                discount_factor = 1 - (line.discount / 100.0)
                line.material_amount = line.material_price_unit * line.product_uom_qty * discount_factor
                
                # Transport is the difference
                line.transport_amount = line.price_subtotal - line.material_amount
            else:
                # If no material price is set, everything is material (not incorporated)
                line.material_amount = line.price_subtotal
                line.transport_amount = 0.0

    def write(self, vals):
        """
        Prevent modification of incorporated order lines
        Allow modification only if transport is not incorporated or if we're in incorporation process
        """
        # Check if we're trying to modify protected fields
        protected_fields = {
            'product_id', 'product_uom_qty', 'product_uom', 
            'price_unit', 'discount', 'tax_id'
        }
        
        modifying_protected = bool(protected_fields & set(vals.keys()))
        
        # Allow internal modifications (from incorporation/uncorporation)
        internal_fields = {
            'material_price_unit', 'transport_price_unit', 
            'transport_reference_amount', 'price_unit'
        }
        is_internal_modification = set(vals.keys()).issubset(internal_fields)
        
        for line in self:
            # Check if order is incorporated and we're modifying protected fields
            if (line.order_id.transport_incorporated and 
                modifying_protected and 
                not is_internal_modification and
                not line.product_id.is_transport):
                
                raise UserError(_(
                    'Cannot modify order lines when transport is incorporated. '
                    'Please use "Uncorporate Transport" button first.'
                ))
        
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Prevent adding new lines to incorporated orders
        """
        # Check if any of the new lines are being added to incorporated orders
        for vals in vals_list:
            if 'order_id' in vals:
                order = self.env['sale.order'].browse(vals['order_id'])
                if order.transport_incorporated:
                    raise UserError(_(
                        'Cannot add new lines when transport is incorporated. '
                        'Please use "Uncorporate Transport" button first.'
                    ))
        
        return super().create(vals_list)

    def _prepare_invoice_line(self, **optional_values):
        """
        Copy material and transport prices to invoice line
        Exclude transport lines that are incorporated (price_unit = 0 and transport_reference_amount > 0)
        """
        res = super()._prepare_invoice_line(**optional_values)
        
        # Copy material and transport prices
        res.update({
            'material_price_unit': self.material_price_unit,
            'transport_price_unit': self.transport_price_unit,
        })
        
        return res

    @api.depends('product_id', 'order_id.transport_incorporated', 
                 'transport_reference_amount', 'price_unit')
    def _compute_qty_to_invoice(self):
        """
        Override to set qty_to_invoice to 0 for incorporated transport lines
        This prevents them from appearing in invoices
        """
        res = super()._compute_qty_to_invoice()
        
        for line in self:
            # If this is an incorporated transport line (price_unit = 0 and has reference amount)
            if (line.product_id.is_transport and 
                line.order_id.transport_incorporated and
                line.transport_reference_amount > 0 and
                line.price_unit == 0):
                line.qty_to_invoice = 0.0
        
        return res

    def _get_invoiceable_lines(self):
        """
        Exclude incorporated transport lines from invoicing
        """
        lines = super()._get_invoiceable_lines()
        
        # Filter out incorporated transport lines
        return lines.filtered(
            lambda l: not (
                l.product_id.is_transport and 
                l.order_id.transport_incorporated and
                l.transport_reference_amount > 0 and
                l.price_unit == 0
            )
        )
