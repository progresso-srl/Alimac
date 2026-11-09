# Copyright 2014-2024 Dinamiche Aziendali srl
# Copyright 2024 Nextev srl
# Copyright 2026 Progresso srl (port to 19.0)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "ITA - Documento di trasporto",
    "version": "19.0.1.0.0",
    "category": "Localization/Italy",
    "summary": "Documento di Trasporto (DDT) for Italian localization",
    "description": """
ITA - Documento di trasporto
============================

Gestione dei DDT (Documenti di Trasporto) per la localizzazione italiana.

Funzionalità:
- Creazione DDT da picking di magazzino
- Condizioni di trasporto (Porto franco, Porto assegnato, etc.)
- Numerazione sequenziale DDT
- Stampa DDT
- Stato DDT (bozza, confermato, validato, fatturato, annullato)
    """,
    "author": "Dinamiche Aziendali srl, Nextev srl, Progresso srl, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-italy",
    "license": "AGPL-3",
    "depends": [
        "stock",
        "delivery",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/stock_delivery_note_data.xml",
        "views/stock_delivery_note_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
