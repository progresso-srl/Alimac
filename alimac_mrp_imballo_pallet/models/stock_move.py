# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
import logging

from odoo import fields, models
from odoo.tools.misc import clean_context

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    alimac_packing_picking_id = fields.Many2one(
        "stock.picking",
        string="Imballo di riferimento",
        index="btree_not_null",
        readonly=True,
        copy=False,
        help="Trasferimento di imballo che ha generato questo scarico di "
        "materiale di imballo.",
    )

    def _action_done(self, cancel_backorder=False):
        moves_done = super()._action_done(cancel_backorder=cancel_backorder)
        if not self.env.context.get("alimac_skip_auto_validate"):
            moves_done._alimac_auto_validate_next_pickings()
        return moves_done

    def _alimac_auto_validate_next_pickings(self):
        """Convalida i trasferimenti successivi con "Convalida automatica".

        Sostituisce la regola Studio "Validazione prelievo confezionato da
        produzione": vale sia dopo la chiusura dell'MO (movimenti finiti) sia
        dopo un trasferimento (es. Imballo -> Prelievo confezionato).
        """
        pickings = self.move_dest_ids.picking_id.filtered(
            lambda p: p.picking_type_id.alimac_auto_validate
            and p.state == "assigned"
        )
        for picking in pickings:
            picking = picking.with_context(clean_context(self.env.context))
            # Colli interi: la merce resta nel suo collo anche a destinazione.
            picking._check_entire_pack()
            picking.move_ids.picked = True
            picking.with_context(skip_backorder=True).button_validate()
            if picking.state == "done":
                picking.message_post(
                    body=self.env._("Convalidato automaticamente (Convalida automatica).")
                )
            else:
                _logger.warning("Convalida automatica non riuscita per %s", picking.name)
