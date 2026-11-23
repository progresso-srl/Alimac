# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

RATE_TYPES = [
    ("ton", "€/t"),
    ("trip", "€/viaggio"),
]


class SaleAddressTransportRate(models.Model):
    _name = "sale.address.transport.rate"
    _description = "Tariffa trasporto per indirizzo di consegna"
    _order = "commercial_partner_id, partner_id, warehouse_id, date_from desc, id desc"
    _rec_name = "partner_id"

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Azienda",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    partner_id = fields.Many2one(
        "res.partner",
        string="Indirizzo di consegna",
        required=True,
        ondelete="cascade",
        index=True,
        domain=[("type", "=", "delivery")],
    )
    commercial_partner_id = fields.Many2one(
        related="partner_id.commercial_partner_id",
        string="Cliente",
        store=True,
        index=True,
    )
    city = fields.Char(related="partner_id.city", string="Città")
    zip = fields.Char(related="partner_id.zip", string="CAP")
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Magazzino/Stabilimento",
        help="Magazzino di partenza dell'ordine. Vuoto = vale da qualsiasi "
        "magazzino; una tariffa con il magazzino dell'ordine ha la precedenza "
        "su quella generica. Visibile solo se esiste più di un magazzino.",
    )
    rate_type = fields.Selection(
        RATE_TYPES,
        string="Modalità",
        required=True,
        default="ton",
    )
    price = fields.Monetary(
        string="Tariffa",
        currency_field="currency_id",
        required=True,
    )
    date_from = fields.Date(string="Valida dal")
    date_to = fields.Date(string="Valida al")
    note = fields.Char(string="Note")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rate in self:
            if rate.date_from and rate.date_to and rate.date_from > rate.date_to:
                raise ValidationError(
                    _("La data di inizio validità deve precedere la data di fine.")
                )

    @api.constrains("partner_id", "warehouse_id", "company_id", "date_from", "date_to", "active")
    def _check_overlap(self):
        """Una sola tariffa valida per indirizzo + stabilimento a una data,
        altrimenti l'ordine non saprebbe quale usare."""
        for rate in self.filtered("active"):
            others = self.search([
                ("id", "!=", rate.id),
                ("partner_id", "=", rate.partner_id.id),
                ("warehouse_id", "=", rate.warehouse_id.id),
                ("company_id", "=", rate.company_id.id),
            ])
            for other in others:
                start = max(rate.date_from or fields.Date.to_date("1900-01-01"),
                            other.date_from or fields.Date.to_date("1900-01-01"))
                end = min(rate.date_to or fields.Date.to_date("9999-12-31"),
                          other.date_to or fields.Date.to_date("9999-12-31"))
                if start <= end:
                    raise ValidationError(_(
                        "L'indirizzo %(address)s ha già una tariffa valida nello stesso "
                        "periodo%(warehouse)s. Chiudi la tariffa precedente con "
                        "\"Valida al\" prima di inserirne una nuova.",
                        address=rate.partner_id.display_name,
                        warehouse=(_(" per il magazzino/stabilimento %s", rate.warehouse_id.name)
                                   if rate.warehouse_id else ""),
                    ))

    @api.depends("partner_id", "rate_type", "price")
    def _compute_display_name(self):
        for rate in self:
            rate.display_name = "%s – %s" % (
                rate.partner_id.display_name or "",
                rate._format_price(),
            )

    def _format_price(self):
        """Es. "25,00 €/t" oppure "450,00 €/viaggio"."""
        self.ensure_one()
        suffix = "/t" if self.rate_type == "ton" else _("/viaggio")
        amount = self.currency_id.format(self.price) if self.currency_id else str(self.price)
        return amount + suffix

    @api.model
    def _find_rate(self, address, warehouse=None, date=None, company=None):
        """Tariffa valida per l'indirizzo alla data. Se esiste, vince quella
        dello stabilimento dell'ordine; altrimenti quella senza stabilimento."""
        if not address:
            return self.browse()
        date = date or fields.Date.context_today(self)
        company = company or self.env.company
        rates = self.search([
            ("partner_id", "=", address.id),
            ("company_id", "=", company.id),
            ("warehouse_id", "in", [warehouse.id, False] if warehouse else [False]),
            "|", ("date_from", "=", False), ("date_from", "<=", date),
            "|", ("date_to", "=", False), ("date_to", ">=", date),
        ])
        return rates.sorted(lambda r: (not r.warehouse_id, -(r.date_from or date).toordinal()))[:1]
