# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    alimac_packing_picking_id = fields.Many2one(
        "stock.picking",
        string="Imballo di riferimento",
        index="btree_not_null",
        readonly=True,
        copy=False,
        help="Trasferimento di imballo che ha generato questo scarico di "
        "materiale di imballo.",
    )
