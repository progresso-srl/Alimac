# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    # Stessa regola dell'analisi vendite. Importi in valuta aziendale e con il
    # segno di price_subtotal del report (note di credito negative): la quota
    # trasporto della riga è ripartita in proporzione su -balance.
    material_amount = fields.Float(string='Material Amount', readonly=True)
    transport_amount = fields.Float(string='Transport Amount', readonly=True)

    @api.model
    def _select(self) -> SQL:
        return SQL(
            """%s,
                -line.balance * account_currency_table.rate - (%s) AS material_amount,
                %s AS transport_amount""",
            super()._select(),
            self._transport_amount_sql(),
            self._transport_amount_sql(),
        )

    @api.model
    def _transport_amount_sql(self) -> SQL:
        return SQL("""
                CASE
                    WHEN template.is_transport THEN -line.balance * account_currency_table.rate
                    WHEN COALESCE(line.transport_amount, 0.0) = 0.0 OR COALESCE(line.price_subtotal, 0.0) = 0.0 THEN 0.0
                    ELSE -line.balance * account_currency_table.rate * line.transport_amount / line.price_subtotal
                END""")
