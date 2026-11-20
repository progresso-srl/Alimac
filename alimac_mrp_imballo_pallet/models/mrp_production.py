# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    alimac_packing_picking_ids = fields.Many2many(
        "stock.picking",
        string="Imballi",
        compute="_compute_alimac_packing_picking_ids",
    )
    alimac_packing_picking_count = fields.Integer(
        compute="_compute_alimac_packing_picking_ids",
    )
    alimac_sale_uom_id = fields.Many2one(
        "uom.uom",
        string="Imballaggio ordinato",
        compute="_compute_alimac_sale_packaging",
        help="Unità della riga d'ordine di vendita che ha generato la "
        "produzione (es. Pallet 1500kg - 20kg x 75).",
    )
    alimac_sale_uom_qty = fields.Float(
        string="Qtà imballaggio",
        compute="_compute_alimac_sale_packaging",
        digits="Product Unit",
        help="Quantità da produrre espressa nell'imballaggio ordinato "
        "(es. 150 Sacco 20kg = 2 Pallet 1500kg - 20kg x 75).",
    )
    alimac_sale_packaging_summary = fields.Char(
        string="Imballaggio",
        compute="_compute_alimac_sale_packaging",
        help="Imballaggi ordinati, es. \"2 Pallet 1500kg - 20kg x 75\" oppure, se "
        "Odoo ha unito più righe nello stesso MO, \"2 Pallet ... + 3 Sacco 25kg\".",
    )
    alimac_packaging_mismatch = fields.Boolean(
        compute="_compute_alimac_sale_packaging",
        help="L'unità dell'MO non corrisponde al formato ordinato: manca la "
        "distinta per quel formato di sacco.",
    )

    def _alimac_get_linked_packing_pickings(self):
        """Trasferimenti di imballo dell'MO.

        Collegati dalla catena (regole "Attiva altra regola") oppure, con le
        regole "Preleva da giacenza, se non disponibile attiva un'altra regola"
        (che su Odoo 19 non collegano i movimenti), con lo stesso riferimento
        dell'MO (es. l'ordine di vendita) e lo stesso prodotto.
        """
        self.ensure_one()
        finished_moves = self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id
        )
        pickings = finished_moves.move_dest_ids.picking_id.filtered(
            lambda p: p.picking_type_id.alimac_is_pallet_packing
        )
        if not pickings and self.reference_ids:
            pickings = self.env["stock.picking"].search(
                [
                    ("reference_ids", "in", self.reference_ids.ids),
                    ("picking_type_id.alimac_is_pallet_packing", "=", True),
                    ("move_ids.product_id", "=", self.product_id.id),
                    ("location_id", "child_of", self.location_dest_id.id),
                    ("company_id", "=", self.company_id.id),
                ],
                order="id",
            )
        return pickings

    def _alimac_get_sale_lines(self):
        """Righe di vendita che hanno generato l'MO.

        Odoo unisce in un solo MO le richieste dello stesso prodotto, tipo
        operazione e ordine (es. 2 pallet 25x60 + 3 sacchi 25 kg = 123 sacchi):
        in quel caso le righe sono più di una.
        """
        self.ensure_one()
        moves = self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id
        ).move_dest_ids
        seen = self.env["stock.move"]
        while moves:
            if moves.sale_line_id:
                return moves.sale_line_id
            seen |= moves
            moves = moves.move_dest_ids - seen
        if not self.reference_ids:
            return self.env["sale.order.line"]
        candidates = self.env["stock.move"].search(
            [
                ("reference_ids", "in", self.reference_ids.ids),
                ("product_id", "=", self.product_id.id),
                ("sale_line_id", "!=", False),
            ]
        ).sale_line_id
        matching = candidates.filtered(self._alimac_is_produced_in_mo_uom)
        return matching or candidates

    def _alimac_is_produced_in_mo_uom(self, sale_line):
        """Un pallet si produce nel suo sacco; un sacco si produce in se stesso."""
        uom = sale_line.product_uom_id
        return self.product_uom_id in (uom | uom.relative_uom_id)

    @api.depends(
        "product_qty",
        "product_uom_id",
        "move_finished_ids.move_dest_ids.sale_line_id",
        "move_finished_ids.move_dest_ids.move_dest_ids",
        "reference_ids",
    )
    def _compute_alimac_sale_packaging(self):
        for production in self:
            sale_lines = (
                production._alimac_get_sale_lines()
                if production.id
                else self.env["sale.order.line"]
            )
            sale_uom = sale_lines.product_uom_id if len(sale_lines) == 1 else False
            production.alimac_sale_uom_id = sale_uom
            production.alimac_sale_uom_qty = (
                production.product_uom_id._compute_quantity(
                    production.product_qty, sale_uom, round=False
                )
                if sale_uom and production.product_uom_id
                else 0.0
            )
            if sale_uom:
                summary = "%s %s" % (
                    "%g" % round(production.alimac_sale_uom_qty, 3), sale_uom.name
                )
            else:
                summary = " + ".join(
                    "%s %s" % ("%g" % line.product_uom_qty, line.product_uom_id.name)
                    for line in sale_lines
                )
            production.alimac_sale_packaging_summary = summary or False
            production.alimac_packaging_mismatch = bool(
                sale_lines
                and production.product_uom_id
                and not all(
                    production._alimac_is_produced_in_mo_uom(line) for line in sale_lines
                )
            )

    def _compute_alimac_packing_picking_ids(self):
        Picking = self.env["stock.picking"]
        for production in self:
            pickings = Picking
            if production.id:
                pickings = production._alimac_get_linked_packing_pickings()
                pickings |= Picking.search(
                    [("alimac_production_id", "=", production.id)]
                )
            production.alimac_packing_picking_ids = pickings
            production.alimac_packing_picking_count = len(pickings)

    def action_alimac_open_pallet_packing(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Imballa"),
            "res_model": "alimac.pallet.packing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_production_id": self.id},
        }

    def action_alimac_view_packing_pickings(self):
        self.ensure_one()
        pickings = self.alimac_packing_picking_ids
        action = {
            "type": "ir.actions.act_window",
            "name": self.env._("Imballi"),
            "res_model": "stock.picking",
            "context": {"create": False},
        }
        if len(pickings) == 1:
            action.update(view_mode="form", res_id=pickings.id)
        else:
            action.update(view_mode="list,form", domain=[("id", "in", pickings.ids)])
        return action
