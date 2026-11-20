# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class StockRoute(models.Model):
    _inherit = "stock.route"

    alimac_uom_selectable = fields.Boolean(
        string="Unità di misura",
        help="La rotta si può collegare alle unità di misura: scegliendo "
        "quell'unità su una riga d'ordine di vendita, la rotta viene "
        "proposta in automatico.",
    )
