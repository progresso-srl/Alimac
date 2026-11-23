# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    # Trasporto = quota incorporata nelle righe merce (franco destino)
    #           + righe di prodotti trasporto non incorporate (con addebito).
    # Una riga trasporto incorporata ha imponibile 0: nessun doppio conteggio.
    material_amount = fields.Monetary(string='Material Amount', readonly=True)
    transport_amount = fields.Monetary(string='Transport Amount', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        rate = (
            f"/ {self._case_value_or_one('s.currency_rate')}"
            f" * {self._case_value_or_one('account_currency_table.rate')}"
        )
        res['material_amount'] = f"""CASE WHEN l.product_id IS NOT NULL THEN SUM(
                CASE WHEN t.is_transport THEN 0.0 ELSE COALESCE(l.material_amount, l.price_subtotal) END
                {rate}) ELSE 0 END"""
        res['transport_amount'] = f"""CASE WHEN l.product_id IS NOT NULL THEN SUM(
                CASE WHEN t.is_transport THEN l.price_subtotal ELSE COALESCE(l.transport_amount, 0.0) END
                {rate}) ELSE 0 END"""
        return res
