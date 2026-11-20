# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    alimac_production_id = fields.Many2one(
        "mrp.production",
        string="Produzione imballata",
        index="btree_not_null",
        readonly=True,
        copy=False,
    )
    alimac_material_move_ids = fields.One2many(
        "stock.move",
        "alimac_packing_picking_id",
        string="Materiali di imballo consumati",
        readonly=True,
    )
    alimac_material_move_count = fields.Integer(
        compute="_compute_alimac_material_move_count",
    )

    def _compute_alimac_material_move_count(self):
        for picking in self:
            picking.alimac_material_move_count = len(picking.alimac_material_move_ids)

    def action_alimac_view_material_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Materiali di imballo"),
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": [("alimac_packing_picking_id", "=", self.id)],
            "context": {"create": False},
        }
