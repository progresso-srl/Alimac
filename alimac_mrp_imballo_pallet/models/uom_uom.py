# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    alimac_route_ids = fields.Many2many(
        "stock.route",
        "alimac_uom_route_rel",
        "uom_id",
        "route_id",
        string="Percorsi di vendita",
        domain="[('alimac_uom_selectable', '=', True)]",
        help="Percorsi proposti sulla riga d'ordine di vendita quando si "
        "sceglie questa unità (es. Pallet 1000kg - 25kg x 40 -> rotta del "
        "pallet).",
    )
