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

    @api.model
    def _alimac_tons(self, product, qty):
        """Tonnellate di `qty` (nell'UdM del prodotto) di `product`.
        Se l'UdM del prodotto è un peso si converte; altrimenti si usa il peso
        del prodotto (kg, o lb se configurato)."""
        ton = self.env.ref('uom.product_uom_ton')
        udm = product.uom_id
        if udm._has_common_reference(ton):
            return udm._compute_quantity(qty, ton, round=False)
        if not product.weight:
            return 0.0
        udm_peso = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        return udm_peso._compute_quantity(product.weight * qty, ton, round=False)

    @api.depends(
        'picking_ids',
        'picking_ids.move_ids.product_qty',
        'picking_ids.move_ids.state',
    )
    def _compute_transport_tons(self):
        for note in self:
            moves = note.picking_ids.move_ids.filtered(
                lambda m: m.state == 'done' and m.product_qty > 0
            )
            note.transport_tons = sum(
                self._alimac_tons(m.product_id, m.product_qty) for m in moves
            )
