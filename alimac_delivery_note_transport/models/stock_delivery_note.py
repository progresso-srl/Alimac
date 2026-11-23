# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockDeliveryNote(models.Model):
    _inherit = 'stock.delivery.note'

    # il DDT di l10n_it_delivery_note non ha una valuta
    transport_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Transport Currency',
    )

    transport_cost = fields.Monetary(
        string='Transport Cost',
        currency_field='transport_currency_id',
        help='Cost paid to the carrier for this delivery',
        default=0.0,
        tracking=True,
    )

    transport_tons = fields.Float(
        string='Transport Tonnage',
        compute='_compute_transport_tons',
        store=True,
        digits=(16, 3),
        help='Total tonnes transported: done quantities converted to tonnes, '
             'or product weight × quantity for products not measured by weight',
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
        'picking_ids.move_ids.state',
        'picking_ids.move_ids.quantity',
        'picking_ids.move_ids.product_uom',
    )
    def _compute_transport_tons(self):
        """Tonnellate effettivamente spedite: quantità dei movimenti evasi
        (``quantity``), non la domanda. Su Odoo 19 la domanda resta quella
        iniziale se si spedisce di più o si convalida senza backorder.
        Regola di conversione unica: product._alimac_get_tons (questo modulo)."""
        for note in self:
            moves = note.picking_ids.move_ids.filtered(lambda m: m.state == 'done')
            note.transport_tons = sum(m._alimac_get_tons(done_qty=True) for m in moves)
