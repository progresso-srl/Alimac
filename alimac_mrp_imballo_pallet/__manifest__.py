# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
{
    "name": "Alimac - Imballo pallet da produzione",
    "summary": "Pulsante Imballa sull'ordine di produzione: crea i colli pallet, "
    "scarica i materiali di imballo e lascia l'eccedenza nell'ubicazione sacchi",
    "version": "19.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "author": "Progresso Srl",
    "website": "https://www.progresso.srl",
    "license": "LGPL-3",
    "depends": ["mrp"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_package_type_views.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_quant_views.xml",
        "wizard/alimac_pallet_packing_wizard_views.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
}
