# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    address_transport_rate_ids = fields.One2many(
        "sale.address.transport.rate",
        "partner_id",
        string="Tariffe trasporto",
    )
    address_transport_rate_summary = fields.Char(
        string="Tariffa attuale",
        compute="_compute_address_transport_rate_summary",
    )

    def _compute_address_transport_rate_summary(self):
        Rate = self.env["sale.address.transport.rate"]
        for partner in self:
            if partner.type != "delivery" or not partner.address_transport_rate_ids:
                partner.address_transport_rate_summary = False
                continue
            # Tariffe valide oggi, una per stabilimento
            rates = Rate.search([
                ("partner_id", "=", partner.id),
                "|", ("date_from", "=", False),
                ("date_from", "<=", fields.Date.context_today(self)),
                "|", ("date_to", "=", False),
                ("date_to", ">=", fields.Date.context_today(self)),
            ])
            partner.address_transport_rate_summary = ", ".join(
                (r.warehouse_id.name + ": " if r.warehouse_id else "") + r._format_price()
                for r in rates
            ) or _("Nessuna tariffa valida oggi")
