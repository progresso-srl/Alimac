# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class TransportReportWizard(models.TransientModel):
    _name = 'transport.report.wizard'
    _description = 'Monthly Transport Report Wizard'

    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True, default=lambda self: str(datetime.now().month))

    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: datetime.now().year,
    )

    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        help='Leave empty to include all carriers',
    )

    transport_condition_ids = fields.Many2many(
        'stock.picking.transport.condition',
        string='Transport Conditions',
        default=lambda self: self._default_transport_conditions(),
        help='Transport conditions to include in the report',
    )

    def _default_transport_conditions(self):
        """Default to Porto Franco"""
        porto_franco = self.env.ref(
            'alimac_delivery_note_transport.transport_condition_porto_franco',
            raise_if_not_found=False
        )
        return porto_franco if porto_franco else self.env['stock.picking.transport.condition']

    def action_print_report(self):
        """Generate and print the monthly transport report"""
        self.ensure_one()

        # Validate inputs
        if self.month not in [str(i) for i in range(1, 13)]:
            raise UserError(_('Invalid month selected'))
        
        if self.year < 1900 or self.year > 2100:
            raise UserError(_('Invalid year selected'))

        # Calculate date range
        month_int = int(self.month)
        date_from = datetime(self.year, month_int, 1)
        date_to = date_from + relativedelta(months=1) - relativedelta(days=1)

        # Build domain
        domain = [
            ('date', '>=', date_from.strftime('%Y-%m-%d')),
            ('date', '<=', date_to.strftime('%Y-%m-%d')),
            ('state', 'not in', ('draft', 'cancel')),
            ('carrier_id', '!=', False),
        ]

        # Add transport condition filter
        if self.transport_condition_ids:
            domain.append(('transport_condition_id', 'in', self.transport_condition_ids.ids))

        # Add carrier filter if specified
        if self.carrier_id:
            domain.append(('carrier_id', '=', self.carrier_id.id))

        # Get data using read_group
        report_data = self._prepare_report_data(domain)

        # Prepare context for report
        data = {
            'month': self.month,
            'year': self.year,
            'month_name': dict(self._fields['month'].selection).get(self.month),
            'carrier_id': self.carrier_id.id if self.carrier_id else False,
            'carrier_name': self.carrier_id.name if self.carrier_id else _('All Carriers'),
            'date_from': date_from.strftime('%d/%m/%Y'),
            'date_to': date_to.strftime('%d/%m/%Y'),
            'report_data': report_data,
        }

        return self.env.ref('alimac_delivery_note_transport.action_report_transport_monthly').report_action(self, data=data)

    def _prepare_report_data(self, domain):
        """
        Prepare hierarchical data for the report
        Returns a list of carriers, each with their destinations
        """
        DeliveryNote = self.env['stock.delivery.note']
        
        # Group by carrier first
        carrier_groups = DeliveryNote._read_group(
            domain,
            ['carrier_id'],
            ['carrier_id', 'transport_cost:sum', 'transport_tons:sum', 'id:count'],
            orderby='carrier_id'
        )

        carriers_data = []
        
        for carrier_group in carrier_groups:
            carrier_id = carrier_group['carrier_id'][0] if carrier_group['carrier_id'] else False
            carrier_name = carrier_group['carrier_id'][1] if carrier_group['carrier_id'] else _('No Carrier')
            
            # Now group by destination for this carrier
            carrier_domain = domain + [('carrier_id', '=', carrier_id)]
            
            destination_groups = DeliveryNote._read_group(
                carrier_domain,
                ['destination_partner_id'],
                ['destination_partner_id', 'transport_cost:sum', 'transport_tons:sum', 'id:count'],
                orderby='destination_partner_id'
            )
            
            destinations_data = []
            for dest_group in destination_groups:
                dest_id = dest_group['destination_partner_id'][0] if dest_group['destination_partner_id'] else False
                dest_partner = self.env['res.partner'].browse(dest_id) if dest_id else False
                
                destinations_data.append({
                    'destination_name': dest_partner.name if dest_partner else _('No Destination'),
                    'destination_city': dest_partner.city if dest_partner and dest_partner.city else '',
                    'trip_count': dest_group['id_count'],
                    'tonnage': dest_group['transport_tons'],
                    'cost': dest_group['transport_cost'],
                })
            
            carriers_data.append({
                'carrier_id': carrier_id,
                'carrier_name': carrier_name,
                'destinations': destinations_data,
                'total_trips': carrier_group['id_count'],
                'total_tonnage': carrier_group['transport_tons'],
                'total_cost': carrier_group['transport_cost'],
            })
        
        return carriers_data
