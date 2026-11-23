# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
{
    "name": "Alimac - Tariffe trasporto per indirizzo di consegna",
    "summary": "Tariffa trasporto (€/t o €/viaggio) sull'indirizzo di consegna: "
    "l'ordine di vendita crea e aggiorna da solo la riga trasporto",
    "version": "19.0.1.0.1",
    "description": """
Tariffe trasporto per indirizzo di consegna (Alimac)
====================================================

* Tabella **Tariffe trasporto** sugli indirizzi di consegna (solo contatti di
  tipo Consegna): €/t o €/viaggio, magazzino/stabilimento facoltativo (visibile con più magazzini), validità.
* Menu **Vendite > Ordini > Tariffe trasporto** e **Indirizzi di consegna**.
* Sull'ordine di vendita la tariffa si legge dall'indirizzo di consegna
  (modificabile) e la **riga trasporto** si crea e si aggiorna da sola:
  quantità = tonnellate dell'ordine (€/t) o numero viaggi (€/viaggio).
* Nessuna riga con porto assegnato.
* Quantità consegnata della riga trasporto allineata alle tonnellate spedite.

Indipendente da alimac_sale_transport: se è installato, la riga creata qui è
quella che "Incorpora trasporto" ripartisce sui prodotti.
""",
    "category": "Sales/Sales",
    "author": "Progresso Srl",
    "website": "https://www.progresso.it",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_address_transport_rate_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
