# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    alimac_count_qty = fields.Float(
        string="N",
        compute="_compute_alimac_count_qty",
        store=True,
        aggregator="sum",
        digits="Product Unit",
        help="Giacenza espressa nell'unità di conteggio dell'ubicazione "
        "(es. numero di sacchi o di pallet).",
    )
    alimac_package_type_id = fields.Many2one(
        related="package_id.package_type_id",
        store=True,
        string="Tipologia collo",
    )
    alimac_package_count = fields.Integer(
        string="N colli",
        compute="_compute_alimac_package_count",
        store=True,
        aggregator="sum",
        help="1 per ogni riga di giacenza dentro un collo. Corretto finché "
        "un collo contiene un solo prodotto/lotto (caso Alimac).",
    )

    @api.depends("quantity", "product_uom_id", "location_id.alimac_count_uom_id")
    def _compute_alimac_count_qty(self):
        for quant in self:
            count_uom = quant.location_id.alimac_count_uom_id
            if count_uom and quant.product_uom_id:
                quant.alimac_count_qty = quant.product_uom_id._compute_quantity(
                    quant.quantity, count_uom, round=False
                )
            else:
                quant.alimac_count_qty = 0.0

    @api.depends("package_id")
    def _compute_alimac_package_count(self):
        for quant in self:
            quant.alimac_package_count = 1 if quant.package_id else 0
