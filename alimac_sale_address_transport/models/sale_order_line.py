# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models

from .sale_order import SYNC_CONTEXT_KEY

LINE_TRIGGER_FIELDS = {"product_id", "product_uom_qty", "product_uom_id", "display_type"}


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_address_transport = fields.Boolean(
        string="Riga trasporto da indirizzo",
        readonly=True,
        help="Riga creata e aggiornata dalla tariffa dell'indirizzo di consegna.",
    )

    # Il prezzo della riga trasporto viene dalla tariffa, non dal listino:
    # Odoo non deve ricalcolarlo quando cambiano quantità o unità.
    def _compute_price_unit(self):
        return super(SaleOrderLine, self - self.filtered("is_address_transport"))._compute_price_unit()

    def _compute_discount(self):
        return super(SaleOrderLine, self - self.filtered("is_address_transport"))._compute_discount()

    # ------------------------------------------------------------------
    # Le righe merce cambiano → si riallinea la riga trasporto
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get(SYNC_CONTEXT_KEY):
            lines.filtered(lambda line: not line.is_address_transport).order_id._sync_address_transport_line()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get(SYNC_CONTEXT_KEY) and LINE_TRIGGER_FIELDS & set(vals):
            self.order_id._sync_address_transport_line()
        return res

    def unlink(self):
        orders = self.filtered(lambda line: not line.is_address_transport).order_id
        res = super().unlink()
        if not self.env.context.get(SYNC_CONTEXT_KEY):
            orders.exists()._sync_address_transport_line()
        return res
