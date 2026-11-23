# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super()._action_done()
        # Consegne e resi: riallinea la quantità consegnata della riga trasporto
        self.move_ids.sale_line_id.order_id._sync_address_transport_delivered()
        return res
