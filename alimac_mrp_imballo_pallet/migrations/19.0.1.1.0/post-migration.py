# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import SUPERUSER_ID, api

from odoo.addons.alimac_mrp_imballo_pallet.hooks import post_init_hook


def migrate(cr, version):
    """Aggiornamento da 19.0.1.0.0: stessa migrazione Studio dell'installazione."""
    if not version:
        return
    post_init_hook(api.Environment(cr, SUPERUSER_ID, {}))
