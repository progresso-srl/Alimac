# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    transport_incorporated = fields.Boolean(
        string='Transport Incorporated',
        readonly=True,
        default=False,
        copy=True,
        help='Indicates whether transport costs have been incorporated into product prices',
    )

    def _get_transport_lines(self):
        """Get all transport lines in the order"""
        self.ensure_one()
        return self.order_line.filtered(lambda l: l.product_id.is_transport)

    def _get_product_lines(self):
        """Get all product lines (excluding transport)"""
        self.ensure_one()
        return self.order_line.filtered(lambda l: not l.product_id.is_transport)

    def _check_incorporation_conditions(self):
        """Validate conditions for incorporating transport"""
        self.ensure_one()
        
        # Check if there are transport lines
        transport_lines = self._get_transport_lines()
        if not transport_lines:
            raise UserError(_('No transport line found in this order.'))
        
        # Check if already incorporated
        if self.transport_incorporated:
            raise UserError(_('Transport is already incorporated in this order.'))
        
        # Check if there are invoices
        if self.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
            raise UserError(_('Cannot incorporate transport: this order has posted invoices.'))
        
        return transport_lines

    def _get_tonnage_for_line(self, line):
        """
        Convert line quantity to tonnage (base UoM)
        Returns 0 if conversion is not possible
        """
        if not line.product_id or not line.product_uom:
            return 0.0
        
        # Get the base UoM (should be 'tonne' or similar)
        product = line.product_id
        base_uom = product.uom_id
        
        # Check if we can convert to the base UoM
        if not line.product_uom._compute_quantity(
            1, base_uom, raise_if_failure=False
        ):
            return 0.0
        
        # Convert quantity to tonnage
        try:
            tonnage = line.product_uom._compute_quantity(
                line.product_uom_qty, base_uom
            )
            return tonnage
        except Exception:
            return 0.0

    def _compute_transport_distribution(self, transport_lines, product_lines):
        """
        Compute transport distribution across product lines
        Returns dict mapping line_id to transport amount
        """
        self.ensure_one()
        
        # Calculate total transport amount
        total_transport = sum(line.price_subtotal for line in transport_lines)
        
        # Calculate tonnage for each product line
        line_tonnage = {}
        total_tonnage = 0.0
        
        for line in product_lines:
            tonnage = self._get_tonnage_for_line(line)
            if tonnage > 0:
                line_tonnage[line.id] = tonnage
                total_tonnage += tonnage
        
        # Validate we have tonnage
        if total_tonnage == 0:
            raise UserError(_('Cannot incorporate transport: no product lines with convertible tonnage found.'))
        
        # Check that all product lines have same taxes as transport lines
        transport_taxes = transport_lines[0].tax_id
        for line in product_lines:
            if line_tonnage.get(line.id, 0) > 0:
                if line.tax_id != transport_taxes:
                    raise UserError(_(
                        'Cannot incorporate transport: product line "%s" has different taxes than transport line.'
                    ) % line.product_id.display_name)
        
        # Distribute transport proportionally
        distribution = {}
        for line_id, tonnage in line_tonnage.items():
            distribution[line_id] = (tonnage / total_tonnage) * total_transport
        
        return distribution, total_transport

    def action_incorporate_transport(self):
        """Incorporate transport costs into product prices"""
        for order in self:
            # Validate conditions
            transport_lines = order._check_incorporation_conditions()
            product_lines = order._get_product_lines()
            
            if not product_lines:
                raise UserError(_('No product lines found to distribute transport.'))
            
            # Compute distribution
            distribution, total_transport = order._compute_transport_distribution(
                transport_lines, product_lines
            )
            
            # Update product lines
            for line in product_lines:
                if line.id in distribution:
                    transport_quota = distribution[line.id]
                    
                    # Save material price
                    line.material_price_unit = line.price_unit
                    
                    # Calculate transport quota per unit
                    # If there's a discount, we need to adjust
                    quantity = line.product_uom_qty
                    discount_factor = 1 - (line.discount / 100.0)
                    
                    if quantity > 0 and discount_factor > 0:
                        transport_per_unit = transport_quota / (quantity * discount_factor)
                    else:
                        transport_per_unit = 0.0
                    
                    line.transport_price_unit = transport_per_unit
                    
                    # Update price_unit to include transport
                    line.price_unit = line.material_price_unit + transport_per_unit
            
            # Set transport line to 0 and save reference amount
            for line in transport_lines:
                line.transport_reference_amount = line.price_subtotal
                line.price_unit = 0.0
            
            # Mark as incorporated
            order.transport_incorporated = True

    def action_uncorporate_transport(self):
        """Restore original prices and transport line"""
        for order in self:
            if not order.transport_incorporated:
                raise UserError(_('Transport is not incorporated in this order.'))
            
            # Check if there are posted invoices
            if order.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
                raise UserError(_('Cannot uncorporate transport: this order has posted invoices.'))
            
            # Restore product lines
            product_lines = order._get_product_lines()
            for line in product_lines:
                if line.material_price_unit:
                    line.price_unit = line.material_price_unit
                    line.material_price_unit = 0.0
                    line.transport_price_unit = 0.0
            
            # Restore transport lines
            transport_lines = order._get_transport_lines()
            for line in transport_lines:
                if line.transport_reference_amount:
                    # Restore original price from reference amount
                    if line.product_uom_qty:
                        line.price_unit = line.transport_reference_amount / line.product_uom_qty
                    line.transport_reference_amount = 0.0
            
            # Mark as not incorporated
            order.transport_incorporated = False

    def copy_data(self, default=None):
        """
        When duplicating an order, maintain incorporated state consistently
        Copy transport_incorporated and all related fields
        """
        res = super().copy_data(default=default)
        
        # The copy maintains the incorporated state and all fields are copied
        # This ensures consistency: if transport_incorporated=True, the prices
        # are already incorporated and material/transport fields are preserved
        
        return res
