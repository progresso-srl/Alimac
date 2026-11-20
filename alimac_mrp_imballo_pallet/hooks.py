# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Migrazione dalle personalizzazioni Studio di Alimac.

- Studio ``stock.location.x_studio_imballo_1`` (unità per contare la
  giacenza) -> ``stock.location.alimac_count_uom_id``.
- Regola di automazione "Validazione prelievo confezionato da produzione"
  -> flag ``alimac_auto_validate`` sui tipi operazione "Prelievo
  confezionato"; la regola viene archiviata (non cancellata).

I campi Studio non vengono eliminati: vanno rimossi a mano dopo la verifica
(vedi README).
"""
import logging

_logger = logging.getLogger(__name__)

STUDIO_REL_TABLE = "x_stock_location_uom_uom_rel"
STUDIO_RULE_NAME = "Validazione prelievo confezionato da produzione"
PRELIEVO_TYPE_NAME = "Prelievo confezionato"


def _migrate_count_uom(env):
    cr = env.cr
    cr.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (STUDIO_REL_TABLE,),
    )
    columns = [row[0] for row in cr.fetchall()]
    loc_col = next((c for c in columns if "location" in c), None)
    uom_col = next((c for c in columns if "uom" in c and "location" not in c), None)
    if not (loc_col and uom_col):
        return
    cr.execute(
        f'SELECT "{loc_col}", MIN("{uom_col}") FROM "{STUDIO_REL_TABLE}" GROUP BY "{loc_col}"'  # noqa: S608
    )
    for location_id, uom_id in cr.fetchall():
        location = env["stock.location"].browse(location_id).exists()
        if location and not location.alimac_count_uom_id:
            location.alimac_count_uom_id = uom_id
            _logger.info("Unità di conteggio da Studio: %s -> %s", location.complete_name, uom_id)


def _migrate_auto_validate(env):
    picking_types = env["stock.picking.type"].with_context(active_test=False).search(
        [("name", "=", PRELIEVO_TYPE_NAME)]
    )
    if not picking_types:
        return
    picking_types.alimac_auto_validate = True
    _logger.info("Convalida automatica attivata su %s", picking_types.mapped("display_name"))
    if "base.automation" in env:
        rules = env["base.automation"].search([("name", "=", STUDIO_RULE_NAME)])
        if rules:
            rules.active = False
            _logger.info("Regola di automazione archiviata: %s", STUDIO_RULE_NAME)


def post_init_hook(env):
    _migrate_count_uom(env)
    _migrate_auto_validate(env)
