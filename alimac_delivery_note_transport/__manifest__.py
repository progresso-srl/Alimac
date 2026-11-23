# -*- coding: utf-8 -*-
{
    'name': 'Alimac Delivery Note Transport',
    'version': '19.0.2.1.0',
    'category': 'Warehouse',
    'summary': 'Tonnage on sale orders, transfers and DDT (one conversion rule); '
               'transport costs on DDT and carrier reports (replaces Gestra)',
    'description': """
Alimac Delivery Note Transport
===============================

This module replaces the legacy "Gestra" system for tracking and reporting transport costs.

Purpose:
--------
* Record transport cost paid to carriers on each DDT (Delivery Note)
* Calculate total tonnage transported
* Generate monthly reports by carrier and destination
* Track "Porto Franco" (freight prepaid) shipments

Tonnage (single conversion rule, product._alimac_get_tons):
-----------------------------------------------------------
* Sale order: Qty (t) on each line (with sum) and Total Tonnage, also printed
  on the quotation/order PDF
* Transfer: Tonnage (replaces the two Studio "Peso(ton)" fields)
* DDT: tonnes actually shipped, replacing gross/net weight in kg

Key Features:
-------------
* Transport cost field on DDT (editable even after confirmation)
* Automatic tonnage calculation from stock moves
* Filters and groupings for carrier, destination, month
* Pivot analysis for transport data
* Monthly report wizard replicating Gestra output
* Support for Porto Franco and Con Addebito transport conditions

What operators see:
-------------------
* Transport cost and tonnage on each DDT (tonnes replace gross/net weight in kg
  on the DDT form, the picking DDT tab and the printed DDT)
* Filters to find Porto Franco shipments
* Pivot view: carriers → destinations with costs and tonnage
* Monthly report: "Carrier X made 3 trips to Pisa, N tons, 100€"

Replaces:
---------
Gestra - Internal legacy system from 2001 for transport cost tracking and reporting
    """,
    'author': 'Progresso',
    'website': 'https://www.progresso.it',
    'license': 'LGPL-3',
    'depends': [
        # DDT di l10n_it_progresso (porting 19.0 del modulo OCA)
        'l10n_it_delivery_note',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/transport_condition_data.xml',
        'views/stock_delivery_note_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'wizard/transport_report_wizard_views.xml',
        'report/transport_monthly_report.xml',
        'report/delivery_note_report.xml',
        'report/sale_order_report.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
