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
        """Default to Porto Franco (OCA xmlid)"""
        porto_franco = self.env.ref(
            'l10n_it_delivery_note.transport_condition_PF',
            raise_if_not_found=False,
        )
        return porto_franco or self.env['stock.picking.transport.condition']

    def action_print_report(self):
        self.ensure_one()
        if self.year < 1900 or self.year > 2100:
            raise UserError(_('Invalid year selected'))

        month_int = int(self.month)
        date_from = datetime(self.year, month_int, 1)
        date_to = date_from + relativedelta(months=1) - relativedelta(days=1)

        domain = [
            ('date', '>=', date_from.strftime('%Y-%m-%d')),
            ('date', '<=', date_to.strftime('%Y-%m-%d')),
            ('state', 'not in', ('draft', 'cancel')),
            ('carrier_id', '!=', False),
        ]
        if self.transport_condition_ids:
            domain.append(('transport_condition_id', 'in', self.transport_condition_ids.ids))
        if self.carrier_id:
            domain.append(('carrier_id', '=', self.carrier_id.id))

        report_data = self._prepare_report_data(domain)

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

        return (self.env.ref('alimac_delivery_note_transport.action_report_transport_monthly')
                .report_action(self, data=data))

    # ------------------------------------------------------------------
    # Odoo 17+ _read_group returns tuples, param is order= not orderby=
    #
    #   _read_group(domain, groupby, aggregates, ..., order=...)
    #   returns list of tuples: (carrier_record, cost_sum, tons_sum, count)
    # ------------------------------------------------------------------

    def _prepare_report_data(self, domain):
        DN = self.env['stock.delivery.note']

        # Group by carrier
        carrier_rows = DN._read_group(
            domain,
            groupby=['carrier_id'],
            aggregates=['transport_cost:sum', 'transport_tons:sum', '__count'],
            order='carrier_id ASC',
        )
        # Each row is a tuple: (carrier_record, cost_sum, tons_sum, count)

        carriers_data = []
        for carrier_rec, cost_sum, tons_sum, count in carrier_rows:
            carrier_id = carrier_rec.id if carrier_rec else False
            carrier_name = carrier_rec.display_name if carrier_rec else _('No Carrier')

            # Sub-group by destination for this carrier
            sub_domain = domain + [('carrier_id', '=', carrier_id)]
            dest_rows = DN._read_group(
                sub_domain,
                groupby=['destination_partner_id'],
                aggregates=['transport_cost:sum', 'transport_tons:sum', '__count'],
                order='destination_partner_id ASC',
            )

            destinations_data = []
            for dest_rec, d_cost, d_tons, d_count in dest_rows:
                destinations_data.append({
                    'destination_name': dest_rec.display_name if dest_rec else _('No Destination'),
                    'destination_city': dest_rec.city if dest_rec else '',
                    'trip_count': d_count,
                    'tonnage': d_tons or 0.0,
                    'cost': d_cost or 0.0,
                })

            carriers_data.append({
                'carrier_id': carrier_id,
                'carrier_name': carrier_name,
                'destinations': destinations_data,
                'total_trips': count,
                'total_tonnage': tons_sum or 0.0,
                'total_cost': cost_sum or 0.0,
            })

        return carriers_data
