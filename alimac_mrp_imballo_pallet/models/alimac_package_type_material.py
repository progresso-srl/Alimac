# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AlimacPackageTypeMaterial(models.Model):
    """Materiale di imballo consumato per ogni collo di una tipologia collo.

    Esempio per "Pallet 1500kg": 1 pedana in legno, 0,4 kg di film estensibile.
    Le quantità sono sempre espresse PER COLLO.
    """

    _name = "alimac.package.type.material"
    _description = "Materiale di imballo per tipologia collo"
    _order = "package_type_id, sequence, id"

    sequence = fields.Integer(default=10)
    package_type_id = fields.Many2one(
        "stock.package.type",
        string="Tipologia collo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Materiale",
        required=True,
        domain="[('type', '=', 'consu')]",
    )
    quantity = fields.Float(
        string="Quantità per collo",
        required=True,
        default=1.0,
        digits="Product Unit",
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unità",
        compute="_compute_product_uom_id",
        store=True,
        readonly=False,
        precompute=True,
        required=True,
    )

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            if line.product_id and not line.product_uom_id:
                line.product_uom_id = line.product_id.uom_id

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    self.env._("La quantità per collo deve essere maggiore di zero.")
                )
