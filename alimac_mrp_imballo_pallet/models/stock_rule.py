# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_mo_vals(
        self, product_id, product_qty, product_uom, location_dest_id, name, origin,
        company_id, values, bom,
    ):
        vals = super()._prepare_mo_vals(
            product_id, product_qty, product_uom, location_dest_id, name, origin,
            company_id, values, bom,
        )
        # Tipo operazione del formato richiesto dalla rotta: serve a capire se
        # Odoo ha ripiegato sulla distinta di un altro formato.
        vals["alimac_format_picking_type_id"] = self.picking_type_id.id
        return vals

    def _should_auto_confirm_procurement_mo(self, p):
        if p.alimac_is_format_fallback:
            # Distinta di un altro formato: l'MO resta in bozza per poterla
            # correggere prima della conferma.
            return False
        return super()._should_auto_confirm_procurement_mo(p)
