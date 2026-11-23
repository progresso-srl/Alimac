# -*- coding: utf-8 -*-

from odoo import models

# Precisione delle tonnellate su ordini, trasferimenti e DDT
TONS_DIGITS = (16, 3)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _alimac_get_tons(self, qty, uom=None):
        """Tonnellate di `qty` espresse in `uom` (UdM del prodotto se vuota).

        Regola unica Alimac per ordine di vendita, trasferimento e DDT:
        - UdM di peso (t, kg, Sacco 25kg o Pallet definiti dal kg): conversione diretta;
        - altrimenti peso del prodotto x quantità nell'UdM del prodotto;
        - 0 se non è un peso e il prodotto non ha peso.

        In Odoo 19 ``_compute_quantity`` non fallisce mai tra UdM non
        compatibili (moltiplica i fattori): per questo si controlla prima
        ``_has_common_reference``.
        """
        self.ensure_one()
        uom = uom or self.uom_id
        if not qty or not uom:
            return 0.0
        ton = self.env.ref('uom.product_uom_ton')
        if uom._has_common_reference(ton):
            return uom._compute_quantity(qty, ton, round=False)
        if not self.weight:
            return 0.0
        base_qty = uom._compute_quantity(qty, self.uom_id, round=False)
        weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        return weight_uom._compute_quantity(self.weight * base_qty, ton, round=False)
