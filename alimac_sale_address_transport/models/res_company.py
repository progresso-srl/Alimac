# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    address_transport_product_id = fields.Many2one(
        "product.product",
        string="Prodotto trasporto",
        domain=[("type", "=", "service"), ("sale_ok", "=", True)],
        help="Prodotto usato per la riga trasporto creata dalle tariffe "
        "degli indirizzi di consegna.",
    )
