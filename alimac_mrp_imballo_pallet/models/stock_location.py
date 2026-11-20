# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    alimac_count_uom_id = fields.Many2one(
        "uom.uom",
        string="Unità di conteggio",
        help="Unità in cui contare la giacenza di questa ubicazione "
        "(es. Sacco 20kg in WH/Confezionato/Sacco20kg, Pallet 1500kg - "
        "20kg x 75 nell'ubicazione dei pallet). Valorizza la colonna N "
        "delle giacenze.",
    )
