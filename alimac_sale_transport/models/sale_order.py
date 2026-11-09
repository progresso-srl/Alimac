# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    transport_incorporated = fields.Boolean(
        string='Transport Incorporated',
        readonly=True,
        default=False,
        copy=True,
        help='Indicates whether transport costs have been incorporated into product prices',
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_transport_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda l: l.product_id.is_transport)

    def _get_product_lines(self):
        self.ensure_one()
        return self.order_line.filtered(
            lambda l: not l.product_id.is_transport and not l.display_type
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_incorporation_conditions(self):
        self.ensure_one()
        transport_lines = self._get_transport_lines()
        if not transport_lines:
            raise UserError(_('No transport line found in this order.'))
        if self.transport_incorporated:
            raise UserError(_('Transport is already incorporated in this order.'))
        if self.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
            raise UserError(_('Cannot incorporate transport: this order has posted invoices.'))
        return transport_lines

    # ------------------------------------------------------------------
    # Tonnage
    # ------------------------------------------------------------------

    @staticmethod
    def _get_tonnage_for_line(line):
        """Convert line qty to base UoM (expected: tonnes). Returns 0 if not convertible."""
        if not line.product_id or not line.product_uom_id:
            return 0.0
        base_uom = line.product_id.uom_id
        try:
            tonnage = line.product_uom_id._compute_quantity(
                line.product_uom_qty, base_uom, raise_if_failure=False,
            )
        except Exception:
            tonnage = 0.0
        return tonnage or 0.0

    # ------------------------------------------------------------------
    # Distribution
    # ------------------------------------------------------------------

    def _compute_transport_distribution(self, transport_lines, product_lines):
        self.ensure_one()
        total_transport = sum(l.price_subtotal for l in transport_lines)

        line_tonnage = {}
        total_tonnage = 0.0
        for line in product_lines:
            t = self._get_tonnage_for_line(line)
            if t > 0:
                line_tonnage[line.id] = t
                total_tonnage += t

        if total_tonnage == 0:
            raise UserError(
                _('Cannot incorporate transport: no product lines with convertible tonnage found.')
            )

        # Tax consistency check
        transport_taxes = transport_lines[0].tax_ids
        for line in product_lines:
            if line_tonnage.get(line.id, 0) > 0 and line.tax_ids != transport_taxes:
                raise UserError(
                    _('Cannot incorporate transport: product line "%s" has different taxes '
                      'than transport line.') % line.product_id.display_name
                )

        # Proportional distribution with rounding remainder on largest line
        prec = self.env['decimal.precision'].precision_get('Product Price')
        distribution = {}
        allocated = 0.0
        largest_id = max(line_tonnage, key=line_tonnage.get)
        for lid, tonnage in line_tonnage.items():
            if lid == largest_id:
                continue
            quota = float_round(
                (tonnage / total_tonnage) * total_transport, precision_digits=prec + 2,
            )
            distribution[lid] = quota
            allocated += quota
        # Remainder goes to the largest line
        distribution[largest_id] = total_transport - allocated

        return distribution, total_transport

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def action_incorporate_transport(self):
        for order in self:
            transport_lines = order._check_incorporation_conditions()
            product_lines = order._get_product_lines()
            if not product_lines:
                raise UserError(_('No product lines found to distribute transport.'))

            distribution, _total = order._compute_transport_distribution(
                transport_lines, product_lines
            )

            # Use context flag so our write() guard lets the changes through
            for line in product_lines.with_context(_transport_incorporating=True):
                if line.id in distribution:
                    quota = distribution[line.id]
                    qty = line.product_uom_qty
                    discount_factor = 1 - (line.discount / 100.0)
                    if qty > 0 and discount_factor > 0:
                        transport_per_unit = quota / (qty * discount_factor)
                    else:
                        transport_per_unit = 0.0
                    line.write({
                        'material_price_unit': line.price_unit,
                        'transport_price_unit': transport_per_unit,
                        'price_unit': line.price_unit + transport_per_unit,
                    })

            for line in transport_lines.with_context(_transport_incorporating=True):
                line.write({
                    'transport_reference_amount': line.price_subtotal,
                    'price_unit': 0.0,
                })

            order.transport_incorporated = True

    def action_uncorporate_transport(self):
        for order in self:
            if not order.transport_incorporated:
                raise UserError(_('Transport is not incorporated in this order.'))
            if order.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
                raise UserError(
                    _('Cannot uncorporate transport: this order has posted invoices.')
                )

            for line in order._get_product_lines().with_context(_transport_incorporating=True):
                if line.material_price_unit:
                    line.write({
                        'price_unit': line.material_price_unit,
                        'material_price_unit': 0.0,
                        'transport_price_unit': 0.0,
                    })

            for line in order._get_transport_lines().with_context(_transport_incorporating=True):
                if line.transport_reference_amount:
                    price = (line.transport_reference_amount / line.product_uom_qty
                             if line.product_uom_qty else 0.0)
                    line.write({
                        'price_unit': price,
                        'transport_reference_amount': 0.0,
                    })

            order.transport_incorporated = False

    # ------------------------------------------------------------------
    # Invoicing: exclude incorporated transport lines
    # ------------------------------------------------------------------

    def _get_invoiceable_lines(self, final=False):
        """In Odoo 19 this is on sale.order, not on sale.order.line."""
        lines = super()._get_invoiceable_lines(final=final)
        return lines.filtered(
            lambda l: not (
                l.product_id.is_transport
                and l.order_id.transport_incorporated
                and l.transport_reference_amount > 0
                and l.price_unit == 0
            )
        )

    # ------------------------------------------------------------------
    # Reports: hide incorporated transport lines from PDF / portal
    # ------------------------------------------------------------------

    def _get_order_lines_to_report(self):
        lines = super()._get_order_lines_to_report()
        if self.transport_incorporated:
            lines = lines.filtered(
                lambda l: not (
                    l.product_id.is_transport
                    and l.transport_reference_amount > 0
                    and l.price_unit == 0
                )
            )
        return lines
