# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # --- Transport line field ---
    transport_reference_amount = fields.Monetary(
        string='Transport Reference Amount',
        currency_field='currency_id',
        help='Original transport amount when incorporated (shown on transport line only)',
        default=0.0,
        copy=True,
    )

    # --- Fields for all lines ---
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

    # --- Computed amounts (stored for reporting) ---
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
        for line in self:
            if line.material_price_unit:
                discount_factor = 1 - (line.discount / 100.0)
                line.material_amount = (
                    line.material_price_unit * line.product_uom_qty * discount_factor
                )
                line.transport_amount = line.price_subtotal - line.material_amount
            else:
                line.material_amount = line.price_subtotal
                line.transport_amount = 0.0

    # ------------------------------------------------------------------
    # Write guard: prevent manual edits on incorporated order lines
    # The context flag _transport_incorporating bypasses the guard
    # so that incorporate/uncorporate buttons AND Odoo internals work.
    # ------------------------------------------------------------------

    def write(self, vals):
        if self.env.context.get('_transport_incorporating'):
            return super().write(vals)

        protected_fields = {
            'product_id', 'product_uom_qty', 'product_uom_id',
            'price_unit', 'discount', 'tax_ids',
        }
        if protected_fields & set(vals.keys()):
            for line in self:
                if (line.order_id.transport_incorporated
                        and not line.product_id.is_transport):
                    raise UserError(_(
                        'Cannot modify order lines when transport is incorporated. '
                        'Please use "Uncorporate Transport" button first.'
                    ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Create guard: prevent adding lines to incorporated orders.
    # System-generated lines (acconti, delivery) pass via context flag.
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('_transport_incorporating'):
            return super().create(vals_list)
        for vals in vals_list:
            order_id = vals.get('order_id')
            if order_id:
                order = self.env['sale.order'].browse(order_id)
                if order.transport_incorporated and not vals.get('display_type'):
                    # Allow section/note lines, and system lines (no product
                    # flagged is_transport can be added, but deposit lines etc.
                    # should go through). We block only if the user is explicitly
                    # adding a product line from the UI.
                    product_id = vals.get('product_id')
                    if product_id:
                        product = self.env['product.product'].browse(product_id)
                        if not product.is_transport:
                            raise UserError(_(
                                'Cannot add new product lines when transport is incorporated. '
                                'Please use "Uncorporate Transport" button first.'
                            ))
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Invoice line preparation
    # ------------------------------------------------------------------

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'material_price_unit': self.material_price_unit,
            'transport_price_unit': self.transport_price_unit,
        })
        return res

    # ------------------------------------------------------------------
    # qty_to_invoice: zero for incorporated transport lines
    # ------------------------------------------------------------------

    @api.depends('product_id', 'order_id.transport_incorporated',
                 'transport_reference_amount', 'price_unit')
    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        for line in self:
            if (line.product_id.is_transport
                    and line.order_id.transport_incorporated
                    and line.transport_reference_amount > 0
                    and line.price_unit == 0):
                line.qty_to_invoice = 0.0
