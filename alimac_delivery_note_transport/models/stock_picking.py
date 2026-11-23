# -*- coding: utf-8 -*-

from odoo import api, fields, models

from .product_product import TONS_DIGITS


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _alimac_get_tons(self, done_qty=False):
        """Tonnellate del movimento.

        `done_qty`: usa sempre la quantità effettiva (``quantity``); altrimenti
        la usa solo se il movimento è evaso o già confermato (picked), se no la
        domanda. Movimenti annullati e prodotti non merce: 0.
        """
        self.ensure_one()
        if self.state == 'cancel' or self.product_id.type != 'consu':
            return 0.0
        if done_qty or self.state == 'done' or self.picked:
            qty = self.quantity
        else:
            qty = self.product_uom_qty
        return self.product_id._alimac_get_tons(qty, self.product_uom)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    alimac_tons = fields.Float(
        string='Tonnage',
        compute='_compute_alimac_tons',
        store=True,
        digits=TONS_DIGITS,
        help='Tonnes of the transfer: actual quantity when done or already '
             'picked, otherwise the demand.',
    )

    # come gli altri dati DDT del trasferimento (peso, colli...): related
    delivery_note_transport_tons = fields.Float(
        related='delivery_note_id.transport_tons',
        string='DN Tonnage',
    )

    @api.depends(
        'move_ids.state',
        'move_ids.picked',
        'move_ids.quantity',
        'move_ids.product_uom_qty',
        'move_ids.product_uom',
        'move_ids.product_id',
    )
    def _compute_alimac_tons(self):
        for picking in self:
            picking.alimac_tons = sum(m._alimac_get_tons() for m in picking.move_ids)
