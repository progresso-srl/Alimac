# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
import re

from markupsafe import Markup

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

FORMAT_PRODUCTION = "production"
FORMAT_PALLET = "pallet"


class AlimacPackagingFormatWizard(models.TransientModel):
    """Configura in un colpo un formato confezionato.

    Formato di produzione (Sacco 10/20/25 kg, Big Bag): ubicazione, tipo
    operazione di produzione e rotta Produzione -> Prelievo -> Consegna.

    Formato pallet (es. Pallet 1500kg - 25kg x 60): ubicazione pallet, tipo
    operazione Imballo e rotta Produzione sacchi -> Imballo -> Prelievo ->
    Consegna. Richiede il formato di produzione del sacco già configurato.

    Riusa ciò che esiste (ricerca per unità di conteggio, ubicazioni dei tipi
    operazione, nome della rotta) e non modifica record esistenti.
    """

    _name = "alimac.packaging.format.wizard"
    _description = "Configura formato confezionato"

    format_type = fields.Selection(
        [
            (FORMAT_PRODUCTION, "Formato di produzione (sacco, big bag)"),
            (FORMAT_PALLET, "Formato pallet (imballo di sacchi)"),
        ],
        string="Tipo di formato",
        required=True,
        default=FORMAT_PRODUCTION,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Magazzino",
        required=True,
        default=lambda self: self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        ),
    )
    company_id = fields.Many2one(related="warehouse_id.company_id")
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unità del formato",
        required=True,
        help="Produzione: es. Sacco 25kg, Big Bag 1500kg.\n"
        "Pallet: es. Pallet 1500kg - 25kg x 60 (riferita al sacco, con "
        "tipologia collo).",
    )
    content_uom_id = fields.Many2one(
        "uom.uom",
        string="Sacco del pallet",
        compute="_compute_content_uom_id",
    )
    package_type_id = fields.Many2one(related="uom_id.package_type_id")
    procure_method = fields.Selection(
        [
            ("make_to_order", "Su ordine: produce sempre la quantità ordinata"),
            ("mts_else_mto", "Da giacenza: usa prima sacchi e pallet a stock"),
        ],
        string="Approvvigionamento",
        required=True,
        default="make_to_order",
        help="Metodo delle regole Prelievo e Imballo della rotta.\n"
        "Su ordine (\"Attiva un'altra regola\"): ogni ordine produce tutta la "
        "quantità ordinata, la giacenza non viene considerata.\n"
        "Da giacenza (\"Preleva da giacenza, se non disponibile attiva un'altra "
        "regola\"): usa prima i sacchi/pallet a stock e produce solo la differenza.",
    )

    parent_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione confezionato",
        required=True,
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        compute="_compute_defaults",
        store=True,
        readonly=False,
        precompute=True,
        help="Ubicazione padre dei formati e di partenza delle consegne "
        "(es. WH/Confezionato).",
    )
    component_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione componenti",
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        compute="_compute_defaults",
        store=True,
        readonly=False,
        precompute=True,
        help="Da dove la produzione preleva sfuso e sacchi vuoti (es. WH/Giacenza).",
    )
    prelievo_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo operazione prelievo",
        domain="[('code', '=', 'internal'), ('company_id', '=', company_id)]",
        compute="_compute_defaults",
        store=True,
        readonly=False,
        precompute=True,
    )
    delivery_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo operazione consegna",
        domain="[('code', '=', 'outgoing'), ('company_id', '=', company_id)]",
        compute="_compute_defaults",
        store=True,
        readonly=False,
        precompute=True,
    )
    material_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione materiali di imballo",
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        compute="_compute_defaults",
        store=True,
        readonly=False,
        precompute=True,
    )
    consumption_location_id = fields.Many2one(
        "stock.location",
        string="Ubicazione di consumo imballi",
        domain="[('usage', 'in', ('production', 'inventory'))]",
        compute="_compute_defaults",
        store=True,
        readonly=False,
        precompute=True,
    )

    location_name = fields.Char(
        string="Nome ubicazione", compute="_compute_names", store=True, readonly=False,
        precompute=True
    )
    picking_type_name = fields.Char(
        string="Nome tipo operazione", compute="_compute_names", store=True, readonly=False,
        precompute=True
    )
    sequence_code = fields.Char(
        string="Prefisso sequenza", compute="_compute_names", store=True, readonly=False,
        precompute=True
    )
    route_name = fields.Char(
        string="Nome rotta", compute="_compute_names", store=True, readonly=False,
        precompute=True
    )

    existing_location_id = fields.Many2one("stock.location", compute="_compute_existing")
    existing_picking_type_id = fields.Many2one(
        "stock.picking.type", compute="_compute_existing"
    )
    existing_route_id = fields.Many2one("stock.route", compute="_compute_existing")
    sack_location_id = fields.Many2one("stock.location", compute="_compute_existing")
    sack_production_type_id = fields.Many2one(
        "stock.picking.type", compute="_compute_existing"
    )
    preview = fields.Html(string="Anteprima", compute="_compute_preview", sanitize=False)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends("uom_id", "format_type")
    def _compute_content_uom_id(self):
        for wizard in self:
            wizard.content_uom_id = (
                wizard.uom_id.relative_uom_id if wizard.format_type == FORMAT_PALLET else False
            )

    @api.depends("warehouse_id")
    def _compute_defaults(self):
        Location = self.env["stock.location"]
        PickingType = self.env["stock.picking.type"]
        for wizard in self:
            warehouse = wizard.warehouse_id
            if not warehouse:
                continue
            company = warehouse.company_id
            wizard.parent_location_id = Location.search(
                [
                    ("usage", "=", "internal"),
                    ("name", "=ilike", "confezionato"),
                    ("warehouse_id", "=", warehouse.id),
                ],
                limit=1,
            ) or warehouse.lot_stock_id
            wizard.component_location_id = warehouse.lot_stock_id
            wizard.material_location_id = warehouse.lot_stock_id
            wizard.prelievo_type_id = PickingType.search(
                [
                    ("code", "=", "internal"),
                    ("company_id", "=", company.id),
                    ("alimac_auto_validate", "=", True),
                ],
                limit=1,
            )
            wizard.delivery_type_id = warehouse.out_type_id
            wizard.consumption_location_id = (
                Location.with_company(company)._alimac_get_consumption_location()
            )

    @api.depends("uom_id", "format_type")
    def _compute_names(self):
        for wizard in self:
            if not wizard.uom_id:
                wizard.location_name = wizard.picking_type_name = False
                wizard.sequence_code = wizard.route_name = False
                continue
            name = wizard.uom_id.name
            compact = re.sub(r"[^0-9A-Za-z]", "", name).upper()[:12]
            wizard.location_name = name
            wizard.route_name = "Vendita confezionato %s" % name
            if wizard.format_type == FORMAT_PALLET:
                wizard.picking_type_name = "Imballo %s" % name
                wizard.sequence_code = "IMB%s" % compact
            else:
                wizard.picking_type_name = "Produzione - %s" % name
                wizard.sequence_code = "MO%s" % compact

    @api.depends(
        "uom_id", "content_uom_id", "format_type", "parent_location_id",
        "location_name", "route_name", "warehouse_id",
    )
    def _compute_existing(self):
        PickingType = self.env["stock.picking.type"]
        Route = self.env["stock.route"]
        for wizard in self:
            location = wizard._find_location(wizard.uom_id, wizard.location_name)
            wizard.existing_location_id = location
            wizard.sack_location_id = False
            wizard.sack_production_type_id = False
            if wizard.format_type == FORMAT_PALLET:
                wizard.existing_picking_type_id = (
                    wizard._find_picking_type("internal", location, packing=True)
                    if location else PickingType
                )
                sack_location = wizard._find_location(wizard.content_uom_id)
                wizard.sack_location_id = sack_location
                if sack_location:
                    wizard.sack_production_type_id = wizard._find_picking_type(
                        "mrp_operation", sack_location
                    )
            else:
                wizard.existing_picking_type_id = (
                    wizard._find_picking_type("mrp_operation", location)
                    if location else PickingType
                )
            wizard.existing_route_id = (
                Route.search(
                    [
                        ("name", "=", wizard.route_name),
                        ("company_id", "in", (wizard.company_id.id, False)),
                    ],
                    limit=1,
                )
                if wizard.route_name else Route
            )

    @api.depends(
        "existing_location_id", "existing_picking_type_id", "existing_route_id",
        "sack_location_id", "sack_production_type_id", "location_name",
        "picking_type_name", "route_name", "format_type", "uom_id",
    )
    def _compute_preview(self):
        for wizard in self:
            if not wizard.uom_id:
                wizard.preview = False
                continue
            rows = [
                ("Ubicazione", wizard.existing_location_id.complete_name,
                 "%s/%s" % (wizard.parent_location_id.complete_name or "", wizard.location_name or "")),
                ("Tipo operazione", wizard.existing_picking_type_id.display_name,
                 wizard.picking_type_name),
                ("Rotta", wizard.existing_route_id.display_name, wizard.route_name),
            ]
            items = Markup("")
            for label, existing, new in rows:
                if existing:
                    items += Markup("<li><b>%s</b>: riuso <i>%s</i></li>") % (label, existing)
                else:
                    items += Markup("<li><b>%s</b>: creo <i>%s</i></li>") % (label, new or "")
            if wizard.format_type == FORMAT_PALLET:
                if wizard.sack_location_id and wizard.sack_production_type_id:
                    items += Markup(
                        "<li><b>Sacco</b>: %s, prodotto da <i>%s</i></li>"
                    ) % (wizard.sack_location_id.complete_name,
                         wizard.sack_production_type_id.display_name)
                else:
                    items += Markup(
                        "<li class='text-danger'><b>Sacco</b>: formato %s non configurato, "
                        "lancia prima il formato di produzione</li>"
                    ) % (wizard.content_uom_id.name or "?")
            if wizard.existing_route_id:
                items += Markup(
                    "<li class='text-warning'>La rotta esiste già: non viene modificata.</li>"
                )
            wizard.preview = Markup("<ul class='mb-0'>%s</ul>") % items

    # ------------------------------------------------------------------
    # Ricerca record esistenti
    # ------------------------------------------------------------------

    def _find_location(self, uom, name=False):
        """Ubicazione del formato: prima per unità di conteggio, poi per nome."""
        self.ensure_one()
        if not uom or not self.parent_location_id:
            return self.env["stock.location"]
        Location = self.env["stock.location"]
        base = [("location_id", "child_of", self.parent_location_id.id), ("usage", "=", "internal")]
        location = Location.search(base + [("alimac_count_uom_id", "=", uom.id)], limit=1)
        if not location and name:
            location = Location.search(
                base + [("location_id", "=", self.parent_location_id.id), ("name", "=ilike", name)],
                limit=1,
            )
        return location

    def _find_picking_type(self, code, dest_location, packing=False):
        domain = [
            ("code", "=", code),
            ("company_id", "=", self.company_id.id),
            ("default_location_dest_id", "=", dest_location.id),
        ]
        if packing:
            domain.append(("alimac_is_pallet_packing", "=", True))
        return self.env["stock.picking.type"].search(domain, limit=1)

    # ------------------------------------------------------------------
    # Creazione
    # ------------------------------------------------------------------

    def _check(self):
        self.ensure_one()
        if not (self.prelievo_type_id and self.delivery_type_id):
            raise UserError(self.env._("Indica il tipo operazione di prelievo e di consegna."))
        if self.format_type == FORMAT_PRODUCTION and not self.component_location_id:
            raise UserError(self.env._("Indica l'ubicazione dei componenti."))
        if self.format_type == FORMAT_PALLET:
            if not self.package_type_id:
                raise UserError(
                    self.env._("L'unità %s non ha una tipologia collo.", self.uom_id.name)
                )
            if not self.content_uom_id:
                raise UserError(
                    self.env._("L'unità %s non è riferita a un sacco.", self.uom_id.name)
                )
            if not (self.sack_location_id and self.sack_production_type_id):
                raise UserError(
                    self.env._(
                        "Configura prima il formato di produzione %s.", self.content_uom_id.name
                    )
                )
            if not (self.material_location_id and self.consumption_location_id):
                raise UserError(
                    self.env._("Indica l'ubicazione dei materiali e quella di consumo imballi.")
                )
        if not (self.location_name and self.picking_type_name and self.route_name):
            raise UserError(self.env._("Compila i nomi di ubicazione, tipo operazione e rotta."))

    def _get_or_create_location(self):
        location = self.existing_location_id
        if location:
            if not location.alimac_count_uom_id:
                location.alimac_count_uom_id = self.uom_id
            return location
        return self.env["stock.location"].create(
            {
                "name": self.location_name,
                "location_id": self.parent_location_id.id,
                "usage": "internal",
                "company_id": self.company_id.id,
                "alimac_count_uom_id": self.uom_id.id,
            }
        )

    def _get_or_create_picking_type(self, location):
        if self.existing_picking_type_id:
            return self.existing_picking_type_id
        warehouse = self.warehouse_id
        if self.format_type == FORMAT_PALLET:
            template = warehouse.int_type_id
            values = {
                "default_location_src_id": self.sack_location_id.id,
                "default_location_dest_id": location.id,
                "alimac_is_pallet_packing": True,
                "alimac_material_location_id": self.material_location_id.id,
                "alimac_consumption_location_id": self.consumption_location_id.id,
                "alimac_auto_validate": False,
            }
        else:
            template = warehouse.manu_type_id
            values = {
                "default_location_src_id": self.component_location_id.id,
                "default_location_dest_id": location.id,
            }
        values.update(
            {
                "name": self.picking_type_name,
                "sequence_code": self.sequence_code,
                "warehouse_id": warehouse.id,
                "company_id": self.company_id.id,
                "active": True,
            }
        )
        return template.copy(values)

    def _rule_vals(self, name, action, src, dest, picking_type, procure_method, sequence):
        return {
            "name": name,
            "action": action,
            "location_src_id": src.id,
            "location_dest_id": dest.id,
            "location_dest_from_rule": True,
            "picking_type_id": picking_type.id,
            "procure_method": procure_method,
            "warehouse_id": self.warehouse_id.id,
            "company_id": self.company_id.id,
            "sequence": sequence,
        }

    def _create_route(self, location, picking_type):
        customers = self.env.ref("stock.stock_location_customers")
        confezionato = self.parent_location_id
        rules = [
            self._rule_vals(
                "Consegna da %s" % confezionato.name, "pull", confezionato, customers,
                self.delivery_type_id, "make_to_order", 10,
            ),
            self._rule_vals(
                "Prelievo %s" % self.uom_id.name, "pull", location, confezionato,
                self.prelievo_type_id, self.procure_method, 20,
            ),
        ]
        if self.format_type == FORMAT_PALLET:
            rules += [
                self._rule_vals(
                    self.picking_type_name, "pull", self.sack_location_id, location,
                    picking_type, self.procure_method, 30,
                ),
                self._rule_vals(
                    "Produzione %s" % self.content_uom_id.name, "manufacture",
                    self.component_location_id or self.sack_production_type_id.default_location_src_id,
                    self.sack_location_id, self.sack_production_type_id, "make_to_stock", 40,
                ),
            ]
        else:
            rules.append(
                self._rule_vals(
                    "Produzione %s" % self.uom_id.name, "manufacture",
                    self.component_location_id, location, picking_type, "make_to_stock", 30,
                )
            )
        return self.env["stock.route"].create(
            {
                "name": self.route_name,
                "company_id": self.company_id.id,
                "sequence": 1,
                "product_selectable": False,
                "sale_selectable": True,
                "rule_ids": [Command.create(vals) for vals in rules],
            }
        )

    def action_configure(self):
        self.ensure_one()
        self._check()
        location = self._get_or_create_location()
        picking_type = self._get_or_create_picking_type(location)
        route = self.existing_route_id or self._create_route(location, picking_type)
        self.prelievo_type_id.alimac_auto_validate = True
        return {
            "type": "ir.actions.act_window",
            "name": route.display_name,
            "res_model": "stock.route",
            "view_mode": "form",
            "res_id": route.id,
            "target": "current",
        }
