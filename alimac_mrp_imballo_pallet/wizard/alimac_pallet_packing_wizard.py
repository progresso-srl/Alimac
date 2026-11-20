# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
import math

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context

# Tolleranza per i conteggi dei colli (evita 2,0000001 colli -> 3 colli).
_EPSILON = 1e-6


class AlimacPalletPackingWizard(models.TransientModel):
    """Imballa la produzione in colli (pallet, big bag, ...).

    1. lavora sul trasferimento di imballo collegato all'MO tramite la rotta
       (oppure ne crea uno se l'MO è per magazzino);
    2. divide la quantità in colli secondo la confezione scelta e fa il
       "Confeziona" con la tipologia collo;
    3. scarica i materiali di imballo configurati sulla tipologia collo;
    4. convalida il trasferimento (con residuo se si imballa meno della
       richiesta).

    L'eccedenza di produzione non viene toccata: resta nell'ubicazione sacchi.
    """

    _name = "alimac.pallet.packing.wizard"
    _description = "Imballo pallet da produzione"

    production_id = fields.Many2one(
        "mrp.production", string="Produzione", required=True, readonly=True
    )
    company_id = fields.Many2one(related="production_id.company_id")
    product_id = fields.Many2one(related="production_id.product_id")
    product_uom_id = fields.Many2one(
        related="product_id.uom_id", string="Unità del prodotto"
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Trasferimento di imballo",
        compute="_compute_picking_id",
        store=True,
        readonly=True,
        help="Imballo generato dalla rotta dell'ordine di vendita. Se vuoto, "
        "ne viene creato uno nuovo (produzione per magazzino).",
    )
    move_id = fields.Many2one("stock.move", compute="_compute_move_id")
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operazione di imballo",
        compute="_compute_picking_type_id",
        store=True,
        readonly=False,
        domain="[('alimac_is_pallet_packing', '=', True), "
        "('company_id', '=', company_id)]",
    )
    source_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione sacchi",
        compute="_compute_source_location_id",
    )
    allowed_packaging_uom_ids = fields.Many2many(
        "uom.uom", compute="_compute_allowed_packaging_uom_ids"
    )
    packaging_uom_id = fields.Many2one(
        "uom.uom",
        string="Confezione",
        compute="_compute_packaging_uom_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', allowed_packaging_uom_ids)]",
        help="Unità di imballaggio del prodotto con una tipologia collo, "
        "es. Pallet 1500kg - 20kg x 75.",
    )
    package_type_id = fields.Many2one(
        "stock.package.type",
        string="Tipologia collo",
        compute="_compute_package_type_id",
        store=True,
        readonly=False,
    )
    content_uom_id = fields.Many2one(
        "uom.uom",
        string="Unità di conteggio",
        compute="_compute_content_uom_id",
        help="Unità in cui si contano i pezzi del collo (es. Sacco 20kg).",
    )
    qty_per_package = fields.Float(
        string="Quantità per collo",
        compute="_compute_qty_per_package",
        store=True,
        readonly=False,
        digits="Product Unit",
    )
    qty_available = fields.Float(
        string="Disponibile da imballare",
        compute="_compute_qty_available",
        digits="Product Unit",
    )
    qty_to_pack = fields.Float(
        string="Quantità da imballare",
        compute="_compute_qty_to_pack",
        store=True,
        readonly=False,
        digits="Product Unit",
    )
    package_count = fields.Integer(
        string="Colli da creare", compute="_compute_package_count"
    )
    last_package_qty = fields.Float(
        string="Quantità ultimo collo",
        compute="_compute_package_count",
        digits="Product Unit",
    )
    material_line_ids = fields.One2many(
        "alimac.pallet.packing.wizard.material",
        "wizard_id",
        string="Materiali di imballo da scaricare",
        compute="_compute_material_line_ids",
        store=True,
        readonly=False,
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends("production_id")
    def _compute_picking_id(self):
        for wizard in self:
            pickings = wizard.production_id._alimac_get_linked_packing_pickings()
            wizard.picking_id = pickings.filtered(
                lambda p: p.state not in ("done", "cancel")
            )[:1]

    @api.depends("picking_id", "product_id")
    def _compute_move_id(self):
        for wizard in self:
            wizard.move_id = wizard.picking_id.move_ids.filtered(
                lambda m: m.product_id == wizard.product_id
                and m.state not in ("done", "cancel")
            )[:1]

    @api.depends("picking_id", "production_id")
    def _compute_picking_type_id(self):
        PickingType = self.env["stock.picking.type"]
        for wizard in self:
            if wizard.picking_id:
                wizard.picking_type_id = wizard.picking_id.picking_type_id
                continue
            domain = [
                ("alimac_is_pallet_packing", "=", True),
                ("company_id", "=", wizard.company_id.id),
            ]
            dest = wizard.production_id.location_dest_id
            wizard.picking_type_id = PickingType.search(
                domain + [("default_location_src_id", "parent_of", dest.id)], limit=1
            ) or PickingType.search(domain, limit=1)

    @api.depends("picking_id", "picking_type_id")
    def _compute_source_location_id(self):
        for wizard in self:
            wizard.source_location_id = (
                wizard.picking_id.location_id
                or wizard.picking_type_id.default_location_src_id
            )

    @api.depends("product_id")
    def _compute_allowed_packaging_uom_ids(self):
        for wizard in self:
            wizard.allowed_packaging_uom_ids = wizard.product_id.uom_ids.filtered(
                "package_type_id"
            )

    @api.depends("move_id", "allowed_packaging_uom_ids")
    def _compute_packaging_uom_id(self):
        for wizard in self:
            allowed = wizard.allowed_packaging_uom_ids
            from_order = wizard.move_id.packaging_uom_id
            if from_order and from_order in allowed:
                wizard.packaging_uom_id = from_order
            elif wizard.packaging_uom_id not in allowed:
                wizard.packaging_uom_id = allowed[:1]

    @api.depends("packaging_uom_id")
    def _compute_package_type_id(self):
        for wizard in self:
            wizard.package_type_id = wizard.packaging_uom_id.package_type_id

    @api.depends("packaging_uom_id", "product_id")
    def _compute_content_uom_id(self):
        for wizard in self:
            wizard.content_uom_id = (
                wizard.packaging_uom_id.relative_uom_id or wizard.product_id.uom_id
            )

    @api.depends("packaging_uom_id", "content_uom_id")
    def _compute_qty_per_package(self):
        for wizard in self:
            if wizard.packaging_uom_id and wizard.content_uom_id:
                wizard.qty_per_package = wizard.packaging_uom_id._compute_quantity(
                    1.0, wizard.content_uom_id, round=False
                )
            else:
                wizard.qty_per_package = 0.0

    @api.depends("move_id", "source_location_id", "content_uom_id", "product_id")
    def _compute_qty_available(self):
        for wizard in self:
            qty = wizard._get_available_qty_product_uom()
            wizard.qty_available = wizard.product_id.uom_id._compute_quantity(
                qty, wizard.content_uom_id, round=False
            ) if wizard.content_uom_id else 0.0

    @api.depends("qty_available", "qty_per_package", "picking_id")
    def _compute_qty_to_pack(self):
        for wizard in self:
            if wizard.picking_id:
                # Imballo da rotta: si imballa quanto richiesto (o il disponibile).
                wizard.qty_to_pack = wizard.qty_available
            elif wizard.qty_per_package > 0:
                # Produzione per magazzino: solo colli completi, il resto
                # rimane come sacchi.
                full = math.floor(wizard.qty_available / wizard.qty_per_package + _EPSILON)
                wizard.qty_to_pack = full * wizard.qty_per_package
            else:
                wizard.qty_to_pack = 0.0

    @api.depends("qty_to_pack", "qty_per_package")
    def _compute_package_count(self):
        for wizard in self:
            if wizard.qty_per_package > 0 and wizard.qty_to_pack > 0:
                count = math.ceil(wizard.qty_to_pack / wizard.qty_per_package - _EPSILON)
                wizard.package_count = count
                wizard.last_package_qty = (
                    wizard.qty_to_pack - (count - 1) * wizard.qty_per_package
                )
            else:
                wizard.package_count = 0
                wizard.last_package_qty = 0.0

    @api.depends("package_type_id", "package_count")
    def _compute_material_line_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            for material in wizard.package_type_id.alimac_material_line_ids:
                commands.append(
                    Command.create(
                        {
                            "product_id": material.product_id.id,
                            "product_uom_id": material.product_uom_id.id,
                            "quantity": material.quantity * wizard.package_count,
                        }
                    )
                )
            wizard.material_line_ids = commands

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_available_qty_product_uom(self):
        """Quantità imballabile, nell'unità del prodotto."""
        self.ensure_one()
        product = self.product_id
        if not product or not self.source_location_id:
            return 0.0
        free_qty = product.with_context(location=self.source_location_id.id).free_qty
        move = self.move_id
        if not move:
            return max(free_qty, 0.0)
        # Imballo da rotta: domanda ancora da imballare, limitata a quanto
        # è già prenotato sul movimento + quanto è libero in ubicazione.
        demand = move.product_uom._compute_quantity(
            move.product_uom_qty, product.uom_id, round=False
        )
        packed = sum(
            move.move_line_ids.filtered("result_package_id").mapped(
                "quantity_product_uom"
            )
        )
        reserved_unpacked = sum(
            move.move_line_ids.filtered(lambda ml: not ml.result_package_id).mapped(
                "quantity_product_uom"
            )
        )
        return max(min(demand - packed, reserved_unpacked + max(free_qty, 0.0)), 0.0)

    def _check_before_packing(self):
        self.ensure_one()
        if self.production_id.state != "done":
            raise UserError(self.env._("Si può imballare solo una produzione completata."))
        if not self.picking_type_id:
            raise UserError(
                self.env._(
                    "Nessuna operazione di imballo trovata: attiva \"Operazione di "
                    "imballo pallet\" sul tipo di operazione (es. Imballo 20x75)."
                )
            )
        if not self.package_type_id:
            raise UserError(
                self.env._("La confezione scelta non ha una tipologia collo.")
            )
        if self.qty_per_package <= 0 or self.qty_to_pack <= 0:
            raise UserError(self.env._("Non c'è nessuna quantità da imballare."))
        if self.qty_to_pack > self.qty_available + _EPSILON:
            raise UserError(
                self.env._(
                    "Quantità da imballare (%(to_pack)s) superiore alla disponibile "
                    "(%(available)s) in %(location)s.",
                    to_pack=self.qty_to_pack,
                    available=self.qty_available,
                    location=self.source_location_id.display_name,
                )
            )
        if self.material_line_ids.filtered(lambda l: l.quantity > 0) and not (
            self.picking_type_id.alimac_material_location_id
            and self.picking_type_id.alimac_consumption_location_id
        ):
            raise UserError(
                self.env._(
                    "Configura l'ubicazione dei materiali di imballo e l'ubicazione "
                    "di consumo sul tipo di operazione %s.",
                    self.picking_type_id.display_name,
                )
            )

    def _create_packing_picking(self, qty_product_uom):
        """Imballo per una produzione senza rotta (produzione per magazzino)."""
        self.ensure_one()
        picking_type = self.picking_type_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": self.production_id.name,
                "alimac_production_id": self.production_id.id,
                "company_id": self.company_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product_id.id,
                            "product_uom": self.product_id.uom_id.id,
                            "product_uom_qty": qty_product_uom,
                            "location_id": picking_type.default_location_src_id.id,
                            "location_dest_id": picking_type.default_location_dest_id.id,
                            "company_id": self.company_id.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        return picking

    def _split_in_packages(self, move_lines, chunks):
        """Assegna le righe prenotate ai colli, spezzandole dove serve.

        :param move_lines: righe non ancora in un collo, prenotate
        :param chunks: lista delle quantità (unità prodotto) di ciascun collo
        :return: colli creati
        """
        uom = self.product_id.uom_id
        queue = list(move_lines)
        packages = self.env["stock.package"]
        for chunk in chunks:
            need = chunk
            lines_for_package = self.env["stock.move.line"]
            while uom.compare(need, 0) > 0:
                if not queue:
                    raise UserError(
                        self.env._("Quantità prenotata insufficiente per creare i colli.")
                    )
                line = queue.pop(0)
                line_qty = line.quantity_product_uom
                if uom.compare(line_qty, need) > 0:
                    # Spezza la riga: 'need' va in questo collo, il resto torna in coda.
                    rest = line_qty - need
                    line.write(
                        {
                            "quantity": uom._compute_quantity(
                                need, line.product_uom_id, rounding_method="HALF-UP"
                            )
                        }
                    )
                    # move_id esplicito: altrimenti la copia della riga
                    # genererebbe un nuovo movimento nel trasferimento.
                    rest_line = line.copy(
                        {
                            "move_id": line.move_id.id,
                            "picking_id": line.picking_id.id,
                            "quantity": uom._compute_quantity(
                                rest, line.product_uom_id, rounding_method="HALF-UP"
                            ),
                            "result_package_id": False,
                            "picked": False,
                        }
                    )
                    queue.insert(0, rest_line)
                    line_qty = need
                lines_for_package |= line
                need -= line_qty
            lines_for_package.write({"picked": True})
            packages |= lines_for_package._put_in_pack(
                package_type_id=self.package_type_id.id
            )
        return packages, self.env["stock.move.line"].concat(*queue)

    def _consume_materials(self, picking, packages):
        """Scarica i materiali di imballo (pattern di stock.scrap)."""
        self.ensure_one()
        picking_type = self.picking_type_id
        src = picking_type.alimac_material_location_id
        dest = picking_type.alimac_consumption_location_id
        origin = "%s - %s" % (picking.name, ", ".join(packages.mapped("name")))
        moves = self.env["stock.move"]
        for line in self.material_line_ids.filtered(lambda l: l.quantity > 0):
            moves |= self.env["stock.move"].create(
                {
                    "origin": origin,
                    "company_id": self.company_id.id,
                    "product_id": line.product_id.id,
                    "product_uom": line.product_uom_id.id,
                    "product_uom_qty": line.quantity,
                    "location_id": src.id,
                    "location_dest_id": dest.id,
                    "alimac_packing_picking_id": picking.id,
                    "picked": True,
                    "move_line_ids": [
                        Command.create(
                            {
                                "product_id": line.product_id.id,
                                "product_uom_id": line.product_uom_id.id,
                                "quantity": line.quantity,
                                "location_id": src.id,
                                "location_dest_id": dest.id,
                            }
                        )
                    ],
                }
            )
        moves._action_done()
        return moves

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_pack(self):
        self.ensure_one()
        # Il wizard è aperto con default_production_id nel contesto: va tolto,
        # altrimenti i movimenti creati da Odoo (es. backorder) lo ereditano.
        self = self.with_context(clean_context(self.env.context))  # noqa: PLW0642
        self._check_before_packing()
        product = self.product_id
        uom = product.uom_id
        total = self.content_uom_id._compute_quantity(
            self.qty_to_pack, uom, round=False
        )
        per_package = self.content_uom_id._compute_quantity(
            self.qty_per_package, uom, round=False
        )

        picking = self.picking_id or self._create_packing_picking(total)
        if picking.state == "draft":
            picking.action_confirm()
        picking.action_assign()

        move = picking.move_ids.filtered(
            lambda m: m.product_id == product and m.state not in ("done", "cancel")
        )[:1]
        if not move:
            raise UserError(
                self.env._("Il trasferimento %s non ha il prodotto da imballare.", picking.name)
            )
        lines = move.move_line_ids.filtered(lambda ml: not ml.result_package_id).sorted("id")
        reserved = sum(lines.mapped("quantity_product_uom"))
        if uom.compare(reserved, total) < 0:
            raise UserError(
                self.env._(
                    "In %(location)s sono prenotati %(reserved)s %(uom)s, ne servono "
                    "%(needed)s. Controlla la giacenza dei sacchi.",
                    location=picking.location_id.display_name,
                    reserved=reserved,
                    needed=total,
                    uom=uom.name,
                )
            )

        count = self.package_count
        chunks = [per_package] * (count - 1) + [total - per_package * (count - 1)]
        packages, leftover_lines = self._split_in_packages(lines, chunks)
        # Le righe prenotate in più (si imballa meno della richiesta) vanno
        # liberate: il residuo dell'imballo resta da fare in un backorder.
        leftover_lines.filtered(lambda ml: not ml.picked).unlink()

        picking.with_context(skip_backorder=True).button_validate()
        if picking.state != "done":
            raise UserError(
                self.env._("Il trasferimento %s non è stato convalidato.", picking.name)
            )
        self._consume_materials(picking, packages)

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": picking.id,
            "target": "current",
        }


class AlimacPalletPackingWizardMaterial(models.TransientModel):
    _name = "alimac.pallet.packing.wizard.material"
    _description = "Materiale di imballo da scaricare"

    wizard_id = fields.Many2one(
        "alimac.pallet.packing.wizard", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", string="Materiale", required=True)
    quantity = fields.Float(string="Quantità", digits="Product Unit")
    product_uom_id = fields.Many2one("uom.uom", string="Unità", required=True)
