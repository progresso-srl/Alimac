# Copyright 2026 Progresso srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

# Chiave di contesto con l'id dell'UdM della riga per cui si calcola il prezzo.
CHIAVE_UDM = "progresso_customerinfo_uom_id"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _price_compute(
        self, price_type, uom=False, currency=False, company=None, date=False
    ):
        """La regola di listino "Prezzi del partner" passa qui l'UdM della riga:
        la mettiamo nel contesto per la scelta della riga cliente."""
        prodotti = self
        if price_type == "partner" and uom:
            prodotti = self.with_context(**{CHIAVE_UDM: uom.id})
        return super(ProductProduct, prodotti)._price_compute(
            price_type, uom, currency, company, date=date
        )

    def _select_customerinfo(
        self, partner=False, _quantity=0.0, _date=None, _uom_id=False, params=False
    ):
        """Sceglie la riga cliente in base all'UdM (imballo) della riga d'ordine.

        1. riga cliente con la stessa UdM della riga d'ordine;
        2. altrimenti riga cliente generica, nell'UdM del prodotto;
        3. altrimenti nessuna riga: si usa il prezzo di vendita standard, mai il
           prezzo di un altro imballo.

        A parità di UdM vale l'ordine del modulo OCA (sequenza, quantità minima,
        prezzo) e la riga sulla variante ha la precedenza su quella sul modello.
        Senza UdM nel contesto il comportamento resta quello del modulo OCA
        (es. codice e nome prodotto cliente sulla riga d'ordine).
        """
        udm_id = _uom_id or self.env.context.get(CHIAVE_UDM)
        if isinstance(udm_id, models.BaseModel):
            udm_id = udm_id.id
        if not udm_id or not partner:
            return super()._select_customerinfo(
                partner=partner,
                _quantity=_quantity,
                _date=_date,
                _uom_id=_uom_id,
                params=params,
            )
        self.ensure_one()
        dominio = self._prepare_domain_customerinfo(
            dict(params or {}, partner_id=partner.id)
        )
        righe = self.env["product.customerinfo"].search(
            dominio, order="sequence,min_qty,price,id"
        )

        def prima_valida(candidate):
            return candidate.filtered(lambda c: c.product_id == self)[:1] or (
                candidate.filtered(
                    lambda c: not c.product_id
                    and c.product_tmpl_id == self.product_tmpl_id
                )[:1]
            )

        stessa_udm = prima_valida(
            righe.filtered(lambda c: c.product_uom_id.id == udm_id)
        )
        if stessa_udm:
            return stessa_udm
        return prima_valida(
            righe.filtered(
                lambda c: not c.product_uom_id or c.product_uom_id == self.uom_id
            )
        )
