# Copyright 2026 Progresso srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from .product_pricelist import CHIAVE_UDM


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _is_applicable_for(self, product, qty_in_product_uom):
        """Una regola con un'UdM diversa da quella del prodotto vale solo per
        le righe in quella UdM. Le regole nell'UdM del prodotto restano valide
        per tutte le UdM, con la conversione standard di Odoo."""
        res = super()._is_applicable_for(product, qty_in_product_uom)
        if not res or not self.uom_id or CHIAVE_UDM not in self.env.context:
            return res
        udm_prodotto = product.uom_id
        if self.uom_id == udm_prodotto:
            return res
        udm_riga_id = self.env.context[CHIAVE_UDM] or udm_prodotto.id
        return self.uom_id.id == udm_riga_id
