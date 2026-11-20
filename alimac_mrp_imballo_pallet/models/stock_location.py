# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    alimac_count_uom_id = fields.Many2one(
        "uom.uom",
        string="Unità di conteggio",
        help="Unità in cui contare la giacenza di questa ubicazione "
        "(es. Sacco 20kg in WH/Confezionato/Sacco20kg, Pallet 1500kg - "
        "20kg x 75 nell'ubicazione dei pallet). Valorizza la colonna N "
        "delle giacenze.",
    )

    @api.model
    def _alimac_get_consumption_location(self, create=False):
        """Ubicazione virtuale "Consumo Imballi" (la crea se richiesto)."""
        location = self.search(
            [
                ("usage", "in", ("production", "inventory")),
                ("name", "=ilike", "consumo imballi"),
                ("company_id", "in", (self.env.company.id, False)),
            ],
            limit=1,
        )
        if not location and create:
            location = self.create(
                {
                    "name": "Consumo Imballi",
                    "usage": "production",
                    "location_id": False,
                    "company_id": self.env.company.id,
                }
            )
        return location
