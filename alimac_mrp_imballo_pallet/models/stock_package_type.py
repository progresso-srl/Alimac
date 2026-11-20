# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    alimac_material_line_ids = fields.One2many(
        "alimac.package.type.material",
        "package_type_id",
        string="Materiali di imballo per collo",
        copy=True,
        help="Materiali scaricati dal pulsante Imballa per ogni collo creato "
        "con questa tipologia (pedana, film, cappuccio, ...).",
    )
