# -*- coding: utf-8 -*-
{
    'name': 'Alimac Sale Transport',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Incorporate transport costs into product prices for franco destino sales',
    'description': """
Alimac Sale Transport
=====================

This module allows Alimac to handle "franco destino" sales where:
- Customers see a single price per product (material + transport)
- Internally, the system tracks material price and transport quota separately
- Transport costs are distributed proportionally based on tonnage
- Statistics and reports show material vs transport breakdown

Key Features:
-------------
* Mark products as transport
* Incorporate/uncorporate transport costs with buttons
* Automatic proportional distribution by tonnage
* Hide transport lines from customer-facing documents (PDF, portal, email)
* Track material_price_unit and transport_price_unit on order and invoice lines
* Support for partial deliveries with proportional transport adjustment
    """,
    'author': 'Progresso',
    'website': 'https://www.progresso.it',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'account',
        'l10n_it_edi',
        'uom',
    ],
    'data': [
        'views/product_product_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
