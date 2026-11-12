# Copyright 2026 Progresso srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

# Chiave di contesto con l'UdM della riga (id, o False = UdM del prodotto).
# Odoo 19 non passa l'UdM a _get_applicable_rules né a _is_applicable_for.
CHIAVE_UDM = "progresso_pricelist_uom_id"


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(self, products, quantity, *, uom=None, **kwargs):
        self_udm = self.with_context(**{CHIAVE_UDM: uom.id if uom else False})
        return super(ProductPricelist, self_udm)._compute_price_rule(
            products, quantity, uom=uom, **kwargs
        )

    def _get_applicable_rules(self, products, date, **kwargs):
        """A parità di tipo di applicazione, mette prima le regole nell'UdM della riga.
        Così, per esempio, un ordine in grammi usa la regola in grammi anche se
        quella nell'UdM del prodotto ha una quantità minima più alta."""
        regole = super()._get_applicable_rules(products, date, **kwargs)
        if CHIAVE_UDM not in self.env.context:
            return regole
        udm_id = self.env.context[CHIAVE_UDM]

        def nella_udm_della_riga(regola):
            if not regola.uom_id:
                return False
            prodotto = regola.product_id or regola.product_tmpl_id
            return regola.uom_id.id == (udm_id or prodotto.uom_id.id)

        return regole.sorted(
            lambda r: (r.applied_on, 0 if nella_udm_della_riga(r) else 1)
        )
