# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    route_ids = fields.Many2many(
        compute="_compute_route_ids",
        store=True,
        readonly=False,
        precompute=True,
    )

    @api.depends("product_uom_id")
    def _compute_route_ids(self):
        """Percorso dall'unità di misura (es. Pallet 1000kg - 25kg x 40).

        Si aggiorna quando cambia l'unità; resta modificabile a mano. Unità
        senza percorsi collegati: la riga tiene quello che ha.
        """
        for line in self:
            routes = line.product_uom_id.alimac_route_ids.filtered(
                lambda r: r.company_id in (line.company_id, self.env["res.company"])
            )
            if routes:
                line.route_ids = routes
            else:
                line.route_ids = line.route_ids
