# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import api, fields, models
from odoo.exceptions import UserError


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
    alimac_format_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo operazione del formato",
        readonly=True,
        copy=False,
        help="Tipo operazione della regola di produzione che ha creato l'MO, "
        "cioè quello del formato ordinato (es. Produzione - Sacco 25kg).",
    )
    alimac_is_format_fallback = fields.Boolean(
        string="Distinta di un altro formato",
        compute="_compute_alimac_is_format_fallback",
        help="Odoo non ha trovato la distinta del formato e ha usato quella "
        "di un altro: l'MO resta in bozza.",
    )
    alimac_packaging_mismatch_lines = fields.Char(
        string="Formati senza distinta",
        compute="_compute_alimac_sale_packaging",
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
        """Righe di vendita prodotte da questo MO.

        - righe collegate dalla catena dei movimenti (regole "Attiva un'altra
          regola");
        - righe dello stesso ordine e prodotto la cui regola di produzione
          porta la merce nell'ubicazione di questo MO e sceglie la sua stessa
          distinta. Odoo unisce in un solo MO le richieste con stesso prodotto,
          distinta, destinazione e ordine (es. 2 pallet 25x60 + 3 sacchi 25 kg =
          123 sacchi); e quando un formato non ha la sua distinta ripiega su
          quella di un altro formato: è il caso che fa scattare l'avviso.
        """
        self.ensure_one()
        SaleLine = self.env["sale.order.line"]
        lines = SaleLine
        moves = self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id
        ).move_dest_ids
        seen = self.env["stock.move"]
        while moves:
            lines |= moves.sale_line_id
            seen |= moves
            moves = moves.move_dest_ids - seen
        if not self.reference_ids:
            return lines
        candidates = self.env["stock.move"].search(
            [
                ("reference_ids", "in", self.reference_ids.ids),
                ("product_id", "=", self.product_id.id),
                ("sale_line_id", "!=", False),
            ]
        ).sale_line_id
        for line in candidates - lines:
            rule = self._alimac_get_line_production_rule(line)
            if not rule:
                # Rotta senza regola di produzione: si decide dall'unità.
                if self._alimac_is_produced_in_mo_uom(line):
                    lines |= line
                continue
            # La riga finisce in questo MO se la sua regola porta la merce
            # dove la porta l'MO e sceglie la stessa distinta.
            bom = rule._get_matching_bom(self.product_id, self.company_id, {})
            if (
                rule.location_dest_id == self.location_dest_id
                and self.bom_id
                and bom == self.bom_id
            ):
                lines |= line
        return lines

    def _alimac_get_line_production_rule(self, sale_line):
        """Regola di produzione della rotta della riga (vuota se non c'è)."""
        return sale_line.route_ids.rule_ids.filtered(
            lambda r: r.action == "manufacture"
            and r.company_id in (self.company_id, self.env["res.company"])
        )[:1]

    def _alimac_is_produced_in_mo_uom(self, sale_line):
        """Un pallet si produce nel suo sacco; un sacco si produce in se stesso."""
        uom = sale_line.product_uom_id
        return self.product_uom_id in (uom | uom.relative_uom_id)

    @staticmethod
    def _alimac_format_lines(lines):
        return " + ".join(
            "%s %s" % ("%g" % line.product_uom_qty, line.product_uom_id.name)
            for line in lines
        )

    @api.depends(
        "product_qty",
        "product_uom_id",
        "bom_id",
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
            production.alimac_sale_packaging_summary = (
                production._alimac_format_lines(sale_lines) or False
            )
            wrong_lines = (
                sale_lines.filtered(
                    lambda line: not production._alimac_is_produced_in_mo_uom(line)
                )
                if production.product_uom_id
                else sale_lines.browse()
            )
            production.alimac_packaging_mismatch = bool(wrong_lines)
            production.alimac_packaging_mismatch_lines = (
                production._alimac_format_lines(wrong_lines) or False
            )

    @api.depends("bom_id", "bom_id.picking_type_id", "alimac_format_picking_type_id")
    def _compute_alimac_is_format_fallback(self):
        for production in self:
            expected = production.alimac_format_picking_type_id
            bom_type = production.bom_id.picking_type_id
            production.alimac_is_format_fallback = bool(
                expected and bom_type and bom_type != expected
            )

    def _alimac_find_format_bom(self):
        """Distinta del formato richiesto: stesso tipo operazione della regola."""
        self.ensure_one()
        return self.env["mrp.bom"].search(
            [
                "|",
                ("product_id", "=", self.product_id.id),
                "&",
                ("product_id", "=", False),
                ("product_tmpl_id", "=", self.product_id.product_tmpl_id.id),
                ("picking_type_id", "=", self.alimac_format_picking_type_id.id),
                ("type", "=", "normal"),
                ("company_id", "in", (self.company_id.id, False)),
            ],
            order="sequence, product_id, id",
            limit=1,
        )

    def action_alimac_apply_format_bom(self):
        """Sostituisce la distinta dell'MO in bozza con quella del formato.

        La quantità resta la stessa in peso (es. 100 Sacco 20kg = 2.000 kg ->
        80 Sacco 25kg); tipo operazione e ubicazioni seguono la nuova distinta.
        """
        for production in self:
            if production.state != "draft":
                raise UserError(
                    self.env._("Si può cambiare distinta solo con l'MO in bozza.")
                )
            expected = production.alimac_format_picking_type_id
            if not expected:
                raise UserError(
                    self.env._("L'MO non è stato creato da una rotta di formato.")
                )
            bom = production._alimac_find_format_bom()
            if not bom:
                raise UserError(
                    self.env._(
                        "Non esiste ancora una distinta per %(product)s con tipo "
                        "operazione %(type)s: creala e riprova.",
                        product=production.product_id.display_name,
                        type=expected.display_name,
                    )
                )
            base_uom = production.product_id.uom_id
            qty_base = production.product_uom_id._compute_quantity(
                production.product_qty, base_uom, round=False
            )
            location_dest = production.location_dest_id
            production.write(
                {"bom_id": bom.id, "picking_type_id": bom.picking_type_id.id}
            )
            production.write(
                {
                    "product_uom_id": bom.product_uom_id.id,
                    "product_qty": base_uom._compute_quantity(
                        qty_base, bom.product_uom_id, round=False
                    ),
                    "location_dest_id": location_dest.id,
                }
            )
            production.message_post(
                body=self.env._(
                    "Distinta sostituita con %(bom)s (formato %(type)s).",
                    bom=bom.display_name,
                    type=expected.display_name,
                )
            )
        return True

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
