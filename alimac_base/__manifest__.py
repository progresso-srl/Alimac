# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
{
    "name": "Alimac - Base (ex personalizzazioni Studio)",
    "summary": "Estensioni dei moduli standard che erano in Studio: Codice Gamma "
    "unico tra modello e variante, listino cliente sul contatto, menu e colonne",
    "version": "19.0.1.0.0",
    "description": """
Alimac - Base
=============

Sostituisce le personalizzazioni Studio di Alimac ancora utili.

Solo campi e viste sui moduli standard, nessuna logica di business. Le
tonnellate (ordine, trasferimento, DDT) sono in alimac_delivery_note_transport.

* Prodotto: **Codice Gamma** unico, sulla variante; sul modello si vede e si
  modifica quando c'è una sola variante (come il Riferimento interno).
* Contatto: pulsante **Listino prodotti** (prezzi cliente).
* Menu **Vendite > Report > Righe ordine di vendita** e **Vendite > Prodotti >
  Listino prodotti-clienti**.
* Colonne Studio utili: UdM in Analisi vendite, UdM imballo e peso negli
  elenchi prodotti, tipo operazione negli elenchi distinte.

All'installazione copia i dati Studio e disattiva le viste e i menu Studio
sostituiti. Vedi README.md.
""",
    "category": "Sales/Sales",
    "author": "Progresso Srl",
    "website": "https://www.progresso.it",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "mrp",
        "product_customerinfo",
    ],
    "data": [
        "views/product_views.xml",
        "views/sale_order_views.xml",
        "views/sale_report_views.xml",
        "views/mrp_bom_views.xml",
        "views/res_partner_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
