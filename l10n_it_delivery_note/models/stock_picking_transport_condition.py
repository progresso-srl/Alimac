# Copyright 2014-2024 Dinamiche Aziendali srl
# Copyright 2026 Progresso srl (port to 19.0)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPickingTransportCondition(models.Model):
    _name = "stock.picking.transport.condition"
    _description = "Transport Condition"
    _order = "sequence, name"

    name = fields.Char(
        string="Transport Condition",
        required=True,
        translate=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string="Notes")
