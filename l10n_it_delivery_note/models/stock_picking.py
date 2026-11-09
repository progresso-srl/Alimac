# Copyright 2014-2024 Dinamiche Aziendali srl
# Copyright 2026 Progresso srl (port to 19.0)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_note_ids = fields.Many2many(
        comodel_name="stock.delivery.note",
        relation="stock_delivery_note_stock_picking_rel",
        column1="picking_id",
        column2="delivery_note_id",
        string="Delivery Notes",
    )
