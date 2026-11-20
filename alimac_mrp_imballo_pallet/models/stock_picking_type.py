# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    alimac_is_pallet_packing = fields.Boolean(
        string="Operazione di imballo pallet",
        help="Se attivo, i trasferimenti di questo tipo sono gestiti dal "
        "pulsante Imballa dell'ordine di produzione.",
    )
    alimac_material_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione materiali di imballo",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
        help="Ubicazione da cui vengono scaricati pedane, film e gli altri "
        "materiali di imballo.",
    )
    alimac_consumption_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione di consumo imballi",
        domain="[('usage', 'in', ('production', 'inventory'))]",
        check_company=True,
        help="Ubicazione virtuale in cui finiscono i materiali di imballo "
        "consumati.",
    )
    alimac_auto_validate = fields.Boolean(
        string="Convalida automatica",
        help="Convalida in automatico i trasferimenti di questo tipo appena "
        "il trasferimento o la produzione che li precede è completato e la "
        "merce è tutta disponibile (es. Prelievo confezionato). Lascia "
        "all'utente solo la consegna.",
    )
