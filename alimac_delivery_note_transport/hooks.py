# -*- coding: utf-8 -*-
"""Viste Studio sostituite dalle tonnellate di questo modulo: vengono
disattivate (non cancellate). I campi Studio x_studio_qta_peso,
x_studio_totale_tonnellate (ordine e trasferimento) e x_studio_pesoton vanno
rimossi a mano dopo la verifica (vedi README)."""
import logging

_logger = logging.getLogger(__name__)

STUDIO_TONS_VIEWS = [
    # ordine di vendita: Qtà TON e Totale tonnellate
    'studio_customization.odoo_studio_sale_ord_318a1317-daf9-4456-8ce4-e46242fbbf3b',
    # trasferimento: i due Peso(ton)
    'studio_customization.odoo_studio_stock_pi_20150870-bc19-455a-8d58-e325460957f6',
]


def deactivate_studio_tons_views(env):
    for xmlid in STUDIO_TONS_VIEWS:
        view = env.ref(xmlid, raise_if_not_found=False)
        if view and view._name == 'ir.ui.view' and view.active:
            view.active = False
            _logger.info("Disattivata vista Studio: %s", view.name)


def post_init_hook(env):
    deactivate_studio_tons_views(env)
