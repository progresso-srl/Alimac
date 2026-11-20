# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    alimac_packing_picking_ids = fields.Many2many(
        "stock.picking",
        string="Imballi",
        compute="_compute_alimac_packing_picking_ids",
    )
    alimac_packing_picking_count = fields.Integer(
        compute="_compute_alimac_packing_picking_ids",
    )

    def _alimac_get_linked_packing_pickings(self):
        """Trasferimenti di imballo a valle del prodotto finito (rotta)."""
        self.ensure_one()
        finished_moves = self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id
        )
        return finished_moves.move_dest_ids.picking_id.filtered(
            lambda p: p.picking_type_id.alimac_is_pallet_packing
        )

    def _compute_alimac_packing_picking_ids(self):
        Picking = self.env["stock.picking"]
        for production in self:
            pickings = Picking
            if production.id:
                pickings = production._alimac_get_linked_packing_pickings()
                pickings |= Picking.search(
                    [("alimac_production_id", "=", production.id)]
                )
            production.alimac_packing_picking_ids = pickings
            production.alimac_packing_picking_count = len(pickings)

    def action_alimac_open_pallet_packing(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Imballa"),
            "res_model": "alimac.pallet.packing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_production_id": self.id},
        }

    def action_alimac_view_packing_pickings(self):
        self.ensure_one()
        pickings = self.alimac_packing_picking_ids
        action = {
            "type": "ir.actions.act_window",
            "name": self.env._("Imballi"),
            "res_model": "stock.picking",
            "context": {"create": False},
        }
        if len(pickings) == 1:
            action.update(view_mode="form", res_id=pickings.id)
        else:
            action.update(view_mode="list,form", domain=[("id", "in", pickings.ids)])
        return action
