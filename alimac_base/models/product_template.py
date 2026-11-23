# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Il dato vive sulla variante: sul modello è lo specchio della variante
    # unica, come Riferimento interno e Codice a barre.
    alimac_gamma_code = fields.Char(
        string="Codice Gamma",
        compute="_compute_alimac_gamma_code",
        inverse="_inverse_alimac_gamma_code",
        search="_search_alimac_gamma_code",
        help="Codice articolo nel gestionale Gamma (Team System). Con più "
        "varianti si gestisce sulla singola variante.",
    )

    @api.depends("product_variant_ids.alimac_gamma_code")
    def _compute_alimac_gamma_code(self):
        self._compute_template_field_from_variant_field("alimac_gamma_code")

    def _inverse_alimac_gamma_code(self):
        self._set_product_variant_field("alimac_gamma_code")

    def _search_alimac_gamma_code(self, operator, value):
        return [("product_variant_ids.alimac_gamma_code", operator, value)]

    def _get_related_fields_variant_template(self):
        # valore passato alla creazione del modello -> scritto sulla variante
        return super()._get_related_fields_variant_template() + ["alimac_gamma_code"]
