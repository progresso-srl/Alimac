# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    alimac_customerinfo_count = fields.Integer(
        string="Listino prodotti",
        compute="_compute_alimac_customerinfo_count",
    )

    def _compute_alimac_customerinfo_count(self):
        groups = self.env["product.customerinfo"]._read_group(
            [("partner_id", "in", self.ids)], ["partner_id"], ["__count"]
        )
        counts = {partner.id: count for partner, count in groups}
        for partner in self:
            partner.alimac_customerinfo_count = counts.get(partner.id, 0)

    def action_alimac_open_customerinfo(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Listino prodotti – %s", self.display_name),
            "res_model": "product.customerinfo",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
