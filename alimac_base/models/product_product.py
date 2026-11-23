# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    alimac_gamma_code = fields.Char(
        string="Codice Gamma",
        index="btree_not_null",
        copy=False,
        help="Codice articolo nel gestionale Gamma (Team System).",
    )
