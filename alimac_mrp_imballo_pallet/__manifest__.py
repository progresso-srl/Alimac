# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
{
    "name": "Alimac - Imballo pallet da produzione",
    "summary": "Pulsante Imballa sull'ordine di produzione: crea i colli pallet, "
    "scarica i materiali di imballo, lascia l'eccedenza nell'ubicazione sacchi "
    "e convalida in automatico i prelievi intermedi",
    "version": "19.0.1.4.1",
    "description": """
Imballo pallet da produzione (Alimac)
=====================================

* Pulsante **Imballa** sull'ordine di produzione completato: crea i colli,
  scarica i materiali di imballo, convalida l'Imballo e lascia l'eccedenza
  nell'ubicazione sacchi.
* Flag **Convalida automatica** sui tipi operazione (es. Prelievo
  confezionato): sostituisce la regola Studio.
* Wizard **Configura formato confezionato**: crea ubicazione, tipo operazione
  e rotta di un formato sacco/big bag o pallet.
* Installazione: ubicazione virtuale "Consumo Imballi".
* Percorso collegato all'unità di misura: la riga d'ordine lo propone da sola.
* MO lasciato in bozza se Odoo usa la distinta di un altro formato.
* Giacenze: colonne N (unità di conteggio dell'ubicazione), Tipologia collo,
  N colli.

Documentazione completa nel file README.md del modulo.
""",
    "category": "Manufacturing/Manufacturing",
    "author": "Progresso Srl",
    "license": "LGPL-3",
    "depends": ["mrp", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_package_type_views.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_location_views.xml",
        "views/stock_quant_views.xml",
        "views/stock_route_uom_views.xml",
        "wizard/alimac_pallet_packing_wizard_views.xml",
        "wizard/alimac_packaging_format_wizard_views.xml",
        "views/mrp_production_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
