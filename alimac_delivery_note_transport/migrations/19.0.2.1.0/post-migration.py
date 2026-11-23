# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.alimac_delivery_note_transport.hooks import deactivate_studio_tons_views

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """- Ricalcolo delle tonnellate DDT: ora dalla quantità spedita, non dalla domanda.
    - Nuove tonnellate su ordine e trasferimento: Odoo le calcola da solo
      (campi nuovi); qui si disattivano le viste Studio che sostituiscono."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    notes = env['stock.delivery.note'].with_context(active_test=False).search([])
    env.add_to_compute(notes._fields['transport_tons'], notes)
    env.flush_all()
    _logger.info("Tonnellate ricalcolate su %s DDT", len(notes))
    deactivate_studio_tons_views(env)
