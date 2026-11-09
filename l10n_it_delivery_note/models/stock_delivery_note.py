# Copyright 2014-2024 Dinamiche Aziendali srl
# Copyright 2026 Progresso srl (port to 19.0)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockDeliveryNote(models.Model):
    _name = "stock.delivery.note"
    _description = "Delivery Note (DDT)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"

    name = fields.Char(
        string="DDT Number",
        required=True,
        readonly=True,
        default="/",
        copy=False,
        tracking=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        tracking=True,
    )

    partner_shipping_id = fields.Many2one(
        comodel_name="res.partner",
        string="Shipping Address",
        tracking=True,
    )

    date = fields.Date(
        string="DDT Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Carrier",
        tracking=True,
    )

    transport_condition_id = fields.Many2one(
        comodel_name="stock.picking.transport.condition",
        string="Transport Condition",
        tracking=True,
    )

    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        relation="stock_delivery_note_stock_picking_rel",
        column1="delivery_note_id",
        column2="picking_id",
        string="Pickings",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("done", "Validated"),
            ("invoiced", "Invoiced"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
    )

    note = fields.Html(string="Notes")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
    )

    # ---- Actions / workflow ----

    def action_confirm(self):
        for note in self:
            if note.state != "draft":
                raise UserError(
                    _("Only draft delivery notes can be confirmed.")
                )
            if note.name == "/":
                note.name = self.env["ir.sequence"].next_by_code(
                    "stock.delivery.note"
                ) or "/"
            note.state = "confirm"

    def action_validate(self):
        for note in self:
            if note.state != "confirm":
                raise UserError(
                    _("Only confirmed delivery notes can be validated.")
                )
            note.state = "done"

    def action_invoice(self):
        for note in self:
            note.state = "invoiced"

    def action_cancel(self):
        for note in self:
            note.state = "cancel"

    def action_draft(self):
        for note in self:
            if note.state != "cancel":
                raise UserError(
                    _("Only cancelled delivery notes can be reset to draft.")
                )
            note.state = "draft"
