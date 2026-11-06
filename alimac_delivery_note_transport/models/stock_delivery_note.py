# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockDeliveryNote(models.Model):
    _inherit = 'stock.delivery.note'

    transport_cost = fields.Monetary(
        string='Transport Cost',
        currency_field='currency_id',
        help='Cost paid to the carrier for this delivery',
        default=0.0,
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    transport_tons = fields.Float(
        string='Transport Tonnage',
        compute='_compute_transport_tons',
        store=True,
        digits=(16, 3),
        help='Total tonnage transported (calculated from stock moves in base UoM)',
    )

    # Helper computed field for destination (used in reports and grouping)
    destination_partner_id = fields.Many2one(
        'res.partner',
        string='Destination',
        compute='_compute_destination_partner',
        store=True,
        help='Shipping address or fallback to partner if not set',
    )

    @api.depends('partner_shipping_id', 'partner_id')
    def _compute_destination_partner(self):
        """
        Compute destination: use partner_shipping_id if set, otherwise partner_id
        """
        for note in self:
            note.destination_partner_id = note.partner_shipping_id or note.partner_id

    @api.depends(
        'picking_ids',
        'picking_ids.move_ids',
        'picking_ids.move_ids.product_qty',
        'picking_ids.move_ids.state',
        'picking_ids.state',
    )
    def _compute_transport_tons(self):
        """
        Calculate total tonnage from stock moves
        
        Uses product_qty from stock.move which is already in base UoM (tonnage)
        Only counts moves that are done
        """
        for note in self:
            total_tons = 0.0
            
            # Get all pickings linked to this delivery note
            for picking in note.picking_ids:
                # Only count done moves
                done_moves = picking.move_ids.filtered(
                    lambda m: m.state == 'done' and m.product_qty > 0
                )
                
                # Sum product_qty (already in base UoM = tonnes)
                for move in done_moves:
                    total_tons += move.product_qty
            
            note.transport_tons = total_tons

    def write(self, vals):
        """
        Allow transport_cost to be edited even when DDT is confirmed
        This is an exception to l10n_it_delivery_note's readonly rules
        """
        # The field is not in the readonly list, so it should be editable
        # This override is here as documentation and for potential future customization
        return super().write(vals)
