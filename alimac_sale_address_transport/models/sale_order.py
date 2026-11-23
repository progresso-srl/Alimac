# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

from .sale_address_transport_rate import RATE_TYPES

# Campi dell'ordine che, se cambiano, richiedono di riallineare la riga trasporto.
# default_transport_condition_id esiste solo con l10n_it_delivery_note: come
# chiave di vals è innocuo anche se il modulo non c'è.
SYNC_TRIGGER_FIELDS = {
    "partner_shipping_id",
    "warehouse_id",
    "company_id",
    "order_line",
    "address_transport_type",
    "address_transport_price",
    "address_transport_trips",
    "default_transport_condition_id",
}

SYNC_CONTEXT_KEY = "address_transport_syncing"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    address_transport_rate_id = fields.Many2one(
        "sale.address.transport.rate",
        string="Tariffa indirizzo",
        compute="_compute_address_transport_rate_id",
        store=True,
        copy=False,
        help="Tariffa letta dall'indirizzo di consegna (valida alla data "
        "dell'ordine, preferendo quella del magazzino dell'ordine).",
    )
    address_transport_type = fields.Selection(
        RATE_TYPES,
        string="Modalità trasporto",
        compute="_compute_address_transport_values",
        store=True,
        readonly=False,
    )
    address_transport_price = fields.Monetary(
        string="Tariffa trasporto",
        currency_field="currency_id",
        compute="_compute_address_transport_values",
        store=True,
        readonly=False,
        help="Proposta dall'indirizzo di consegna, modificabile sul singolo "
        "ordine. 0 = nessuna riga trasporto.",
    )
    address_transport_trips = fields.Integer(
        string="N. viaggi",
        default=1,
        help="Quantità della riga trasporto quando la tariffa è a viaggio.",
    )
    address_transport_charged = fields.Boolean(
        string="Trasporto a carico Alimac",
        compute="_compute_address_transport_flags",
        help="Falso con porto assegnato: nessuna riga trasporto.",
    )
    address_transport_missing = fields.Boolean(
        compute="_compute_address_transport_flags",
    )
    address_transport_can_save = fields.Boolean(
        compute="_compute_address_transport_flags",
    )
    address_transport_enabled = fields.Boolean(
        string="Indirizzo di consegna vero",
        compute="_compute_address_transport_flags",
        help="Vero se l'indirizzo di consegna è un contatto di tipo Consegna: "
        "solo in quel caso compare la Tariffa trasporto e si crea la riga.",
    )
    address_transport_frozen = fields.Boolean(
        compute="_compute_address_transport_flags",
        help="Trasporto incorporato nei prezzi (alimac_sale_transport): "
        "tariffa e riga trasporto bloccate finché non si scorpora.",
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends("partner_shipping_id", "warehouse_id", "company_id")
    def _compute_address_transport_rate_id(self):
        # Non dipende da date_order apposta: la conferma riscrive date_order e
        # non deve ricalcolare (e sovrascrivere) una tariffa modificata a mano.
        Rate = self.env["sale.address.transport.rate"]
        for order in self:
            date = (
                fields.Date.to_date(order.date_order)
                if order.date_order
                else fields.Date.context_today(order)
            )
            order.address_transport_rate_id = Rate._find_rate(
                order.partner_shipping_id,
                warehouse=order.warehouse_id,
                date=date,
                company=order.company_id or self.env.company,
            )

    @api.depends("address_transport_rate_id")
    def _compute_address_transport_values(self):
        for order in self:
            rate = order.address_transport_rate_id
            order.address_transport_type = rate.rate_type or order.address_transport_type or "ton"
            order.address_transport_price = rate.price

    @api.depends(
        "partner_shipping_id",
        "partner_shipping_id.type",
        "address_transport_price",
        "address_transport_type",
        "address_transport_rate_id",
    )
    def _compute_address_transport_flags(self):
        for order in self:
            charged = order._address_transport_is_charged()
            rate = order.address_transport_rate_id
            enabled = order._address_transport_is_enabled()
            order.address_transport_enabled = enabled
            order.address_transport_charged = charged
            order.address_transport_frozen = order._address_transport_is_frozen()
            order.address_transport_missing = bool(
                charged
                and enabled
                and order.company_id.address_transport_product_id
                and not order.address_transport_price
            )
            order.address_transport_can_save = bool(
                enabled
                and order.partner_shipping_id.type == "delivery"
                and order.address_transport_price
                and (
                    not rate
                    or rate.rate_type != order.address_transport_type
                    or order.currency_id.compare_amounts(
                        rate.price, order.address_transport_price
                    )
                )
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _address_transport_is_enabled(self):
        """Tariffa trasporto solo su un vero indirizzo di consegna (contatto
        di tipo Consegna). Con l'indirizzo del cliente stesso, o un contatto di
        altro tipo, non compare nulla: si usa la spedizione nativa."""
        self.ensure_one()
        shipping = self.partner_shipping_id
        return bool(shipping and shipping.type == "delivery")

    def _address_transport_is_charged(self):
        """Porto assegnato (l10n_it_delivery_note) = il trasporto lo paga il
        cliente al vettore: nessuna riga. Senza il modulo DDT è sempre vero."""
        self.ensure_one()
        if "default_transport_condition_id" not in self._fields:
            return True
        porto_assegnato = self.env.ref(
            "l10n_it_delivery_note.transport_condition_PA", raise_if_not_found=False
        )
        return not (
            porto_assegnato and self.default_transport_condition_id == porto_assegnato
        )

    def _address_transport_is_frozen(self):
        """Trasporto incorporato con alimac_sale_transport: la riga trasporto è
        stata azzerata e ripartita sui prodotti, non va più toccata.
        Controllo morbido, così il modulo funziona anche da solo."""
        self.ensure_one()
        return "transport_incorporated" in self._fields and self.transport_incorporated

    @api.model
    def _address_transport_tons(self, product, qty, uom):
        """Tonnellate di `qty` espresse in `uom`. Stessa regola di
        alimac_sale_transport: UdM di peso → conversione diretta, altrimenti
        peso del prodotto × quantità."""
        if not product or not uom:
            return 0.0
        ton = self.env.ref("uom.product_uom_ton")
        if uom._has_common_reference(ton):
            return uom._compute_quantity(qty, ton, round=False)
        if not product.weight:
            return 0.0
        base_qty = uom._compute_quantity(qty, product.uom_id, round=False)
        weight_uom = self.env["product.template"]._get_weight_uom_id_from_ir_config_parameter()
        return weight_uom._compute_quantity(product.weight * base_qty, ton, round=False)

    def _get_address_transport_goods_lines(self):
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: not line.display_type
            and not line.is_address_transport
            and not line.is_downpayment
            and line.product_id.type == "consu"
        )

    def _get_address_transport_qty_uom(self, product):
        """Quantità e UdM della riga trasporto."""
        self.ensure_one()
        if self.address_transport_type == "trip":
            return max(self.address_transport_trips, 1), product.uom_id
        tons = sum(
            self._address_transport_tons(line.product_id, line.product_uom_qty, line.product_uom_id)
            for line in self._get_address_transport_goods_lines()
        )
        return tons, self.env.ref("uom.product_uom_ton")

    def _get_address_transport_line_name(self, product):
        self.ensure_one()
        address = self.partner_shipping_id
        place = ", ".join(p for p in (address.street, address.city) if p) or address.display_name
        suffix = "/t" if self.address_transport_type == "ton" else _("/viaggio")
        return "%s – %s (%s%s)" % (
            product.with_context(lang=self.partner_id.lang).display_name,
            place,
            self.currency_id.format(self.address_transport_price),
            suffix,
        )

    # ------------------------------------------------------------------
    # Riga trasporto
    # ------------------------------------------------------------------

    def _sync_address_transport_line(self):
        """Crea, aggiorna o elimina la riga trasporto in base a tariffa,
        porto e tonnellate. Idempotente: si può chiamare quante volte si vuole."""
        if self.env.context.get(SYNC_CONTEXT_KEY):
            return
        for order in self.with_context(**{SYNC_CONTEXT_KEY: True}):
            if order.state == "cancel" or order.locked or order._address_transport_is_frozen():
                continue
            product = order.company_id.address_transport_product_id
            lines = order.order_line.filtered("is_address_transport")
            # Riga già fatturata: non si tocca più
            if any(line.qty_invoiced for line in lines):
                continue
            if not product:
                continue

            qty, uom = order._get_address_transport_qty_uom(product)
            wanted = (
                order._address_transport_is_enabled()
                and order._address_transport_is_charged()
                and order.address_transport_price
                and not float_is_zero(qty, precision_rounding=uom.rounding)
            )
            if not wanted:
                order._remove_address_transport_lines(lines)
                continue

            vals = {
                "product_id": product.id,
                "product_uom_id": uom.id,
                "product_uom_qty": qty,
                "price_unit": order.address_transport_price,
                "discount": 0.0,
                "name": order._get_address_transport_line_name(product),
            }
            if lines:
                line = lines[0]
                order._remove_address_transport_lines(lines - line)
                changed = {
                    key: value
                    for key, value in vals.items()
                    if not order._address_transport_same_value(line, key, value)
                }
                if changed:
                    line.write(changed)
            else:
                last = max(order.order_line.mapped("sequence") or [10])
                self.env["sale.order.line"].with_context(
                    **{SYNC_CONTEXT_KEY: True}
                ).create({
                    **vals,
                    "order_id": order.id,
                    "is_address_transport": True,
                    "sequence": last + 1,
                })

    @api.model
    def _remove_address_transport_lines(self, lines):
        """Su ordine confermato Odoo non permette di eliminare righe: la riga
        trasporto si porta a quantità 0."""
        confirmed = lines.filtered(lambda line: line.state == "sale")
        confirmed.filtered("product_uom_qty").write({"product_uom_qty": 0.0})
        (lines - confirmed).unlink()

    @api.model
    def _address_transport_same_value(self, line, key, value):
        current = line[key]
        if key in ("product_id", "product_uom_id"):
            return current.id == value
        if key == "product_uom_qty":
            return not float_compare(current, value, precision_rounding=line.product_uom_id.rounding)
        if key in ("price_unit", "discount"):
            return not float_compare(current, value, precision_digits=6)
        return current == value

    def _sync_address_transport_delivered(self):
        """Quantità consegnata della riga trasporto (prodotto servizio, quindi
        manuale per Odoo): tonnellate spedite delle righe merce, oppure i viaggi
        dell'ordine appena parte la prima consegna."""
        for order in self:
            lines = order.order_line.filtered("is_address_transport")
            if not lines:
                continue
            goods = order._get_address_transport_goods_lines()
            for line in lines:
                if order.address_transport_type == "trip" or line.product_uom_id != self.env.ref(
                    "uom.product_uom_ton"
                ):
                    delivered = line.product_uom_qty if any(goods.mapped("qty_delivered")) else 0.0
                else:
                    delivered = sum(
                        self._address_transport_tons(g.product_id, g.qty_delivered, g.product_uom_id)
                        for g in goods
                    )
                if float_compare(
                    line.qty_delivered, delivered, precision_rounding=line.product_uom_id.rounding
                ):
                    line.with_context(**{SYNC_CONTEXT_KEY: True}).qty_delivered = delivered

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_address_transport_line()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if SYNC_TRIGGER_FIELDS & set(vals):
            self._sync_address_transport_line()
        return res

    def action_confirm(self):
        self._sync_address_transport_line()
        return super().action_confirm()

    def _get_update_prices_lines(self):
        # "Aggiorna prezzi" non deve riportare la riga trasporto al prezzo di listino
        return super()._get_update_prices_lines().filtered(lambda line: not line.is_address_transport)

    # ------------------------------------------------------------------
    # Pulsanti
    # ------------------------------------------------------------------

    def action_update_address_transport(self):
        """Rilegge la tariffa dall'indirizzo (scarta modifiche manuali) e
        riallinea la riga."""
        for order in self:
            if order._address_transport_is_frozen():
                raise UserError(_(
                    "Il trasporto è incorporato nei prezzi: scorporalo prima di "
                    "aggiornare la tariffa."
                ))
        self._compute_address_transport_rate_id()
        self._compute_address_transport_values()
        self._sync_address_transport_line()
        return True

    def action_save_address_transport_rate(self):
        """Salva la tariffa scritta sull'ordine come tariffa dell'indirizzo di
        consegna (senza magazzino, valida da oggi)."""
        self.ensure_one()
        address = self.partner_shipping_id
        if not address or address.type != "delivery":
            raise UserError(_(
                "Le tariffe si salvano solo su un indirizzo di tipo Consegna."
            ))
        if not self.address_transport_price:
            raise UserError(_("Indica prima la tariffa trasporto sull'ordine."))
        Rate = self.env["sale.address.transport.rate"]
        today = fields.Date.context_today(self)
        current = Rate.search([
            ("partner_id", "=", address.id),
            ("company_id", "=", self.company_id.id),
            ("warehouse_id", "=", False),
            "|", ("date_from", "=", False), ("date_from", "<=", today),
            "|", ("date_to", "=", False), ("date_to", ">=", today),
        ], limit=1)
        vals = {"rate_type": self.address_transport_type, "price": self.address_transport_price}
        if current and current.date_from == today:
            current.write(vals)
            rate = current
        else:
            if current:
                current.date_to = fields.Date.subtract(today, days=1)
            rate = Rate.create({
                **vals,
                "partner_id": address.id,
                "company_id": self.company_id.id,
                "date_from": today,
            })
        self.address_transport_rate_id = rate
        return True
