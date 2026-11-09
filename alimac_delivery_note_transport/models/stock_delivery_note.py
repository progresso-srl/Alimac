# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockDeliveryNote(models.Model):
    _inherit = 'stock.delivery.note'

    transport_cost = fields.Monetary(
        string='Transport Cost',
        help='Cost paid to the carrier for this delivery',
        default=0.0,
        tracking=True,
    )

    transport_tons = fields.Float(
        string='Transport Tonnage',
        compute='_compute_transport_tons',
        store=True,
        digits=(16, 3),
        help='Total tonnage transported (calculated from stock moves in base UoM)',
    )

    destination_partner_id = fields.Many2one(
        'res.partner',
        string='Destination',
        compute='_compute_destination_partner',
        store=True,
        help='Shipping address or fallback to partner if not set',
    )

    @api.depends('partner_shipping_id', 'partner_id')
    def _compute_destination_partner(self):
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
        for note in self:
            total_tons = 0.0
            for picking in note.picking_ids:
                done_moves = picking.move_ids.filtered(
                    lambda m: m.state == 'done' and m.product_qty > 0
                )
                for move in done_moves:
                    total_tons += move.product_qty
            note.transport_tons = total_tons
