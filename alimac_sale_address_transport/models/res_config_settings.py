# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    address_transport_product_id = fields.Many2one(
        related="company_id.address_transport_product_id",
        readonly=False,
    )
