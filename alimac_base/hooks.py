# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Migrazione dalle personalizzazioni Studio di Alimac.

Dati copiati:
- ``product.product.x_studio_codice_gamma_1`` (Sku Gamma) -> ``alimac_gamma_code``;
- ``product.template.x_studio_codice_gamma`` (Codice Gamma) -> ``alimac_gamma_code``
  della variante, solo per i modelli con una sola variante e codice variante vuoto.
  Modelli con più varianti e codice sul modello: solo segnalati nel log.

Le tonnellate (ordine, righe, trasferimento) e le relative viste Studio sono
gestite da alimac_delivery_note_transport.

Viste e menu Studio sostituiti da questo modulo (o da alimac_mrp_imballo_pallet)
vengono disattivati, non cancellati. I campi Studio restano: vanno rimossi a
mano dopo la verifica (vedi README).
"""
import logging

_logger = logging.getLogger(__name__)

STUDIO = "studio_customization."

# Viste Studio sostituite (xmlid nel modulo studio_customization)
STUDIO_VIEWS = [
    # sale.report list: colonna UdM
    "odoo_studio_sale_rep_34dc0763-a02c-4b16-8748-17a3baddaa45",
    # prodotto: Codice Gamma (modello), UdM imballo, Sku Gamma, peso
    "odoo_studio_product__9ad0cb0f-789a-4d1a-a5bd-315e207e0dd3",
    "odoo_studio_product__77acf8c8-3ecf-406d-b31d-4e50acc5e78b",
    "odoo_studio_product__4569801f-d8da-487b-8203-02873f9a8757",
    "odoo_studio_product__75bb0189-3a2f-40a2-9b0b-550457794059",
    # giacenze e ubicazioni: sostituite da alimac_mrp_imballo_pallet
    "odoo_studio_stock_qu_6d0683a5-4491-4786-abea-7186b29d90e2",
    "odoo_studio_stock_lo_f15c5c5a-cb6e-4e77-92a1-462a3888095a",
    # distinte: tipo operazione
    "odoo_studio_mrp_bom__855abd1a-0af0-45e3-a77a-40e58da1e29d",
    # contatto: pulsante Listino prodotti (+ <header> vuoto)
    "odoo_studio_res_part_e7296153-d50b-4504-99ff-9f436ef0e8b8",
]

STUDIO_MENUS = [
    "vendite_righe_ordine_e24800f4-2591-4e0e-ba43-530f59d4ce99",
    "vendite_listino_prod_5af2ddc5-4efd-4158-ad2f-6258228694db",
]


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def _migrate_gamma_code(env):
    cr = env.cr
    if _column_exists(cr, "product_product", "x_studio_codice_gamma_1"):
        cr.execute(
            """
            UPDATE product_product
               SET alimac_gamma_code = TRIM(x_studio_codice_gamma_1)
             WHERE COALESCE(alimac_gamma_code, '') = ''
               AND COALESCE(TRIM(x_studio_codice_gamma_1), '') <> ''
            """
        )
        _logger.info("Codice Gamma da Sku Gamma (variante): %s varianti", cr.rowcount)

    if _column_exists(cr, "product_template", "x_studio_codice_gamma"):
        cr.execute(
            """
            WITH single AS (
                SELECT product_tmpl_id, MIN(id) AS product_id
                  FROM product_product
                 WHERE active
                 GROUP BY product_tmpl_id
                HAVING COUNT(*) = 1
            )
            UPDATE product_product pp
               SET alimac_gamma_code = TRIM(pt.x_studio_codice_gamma)
              FROM single s
              JOIN product_template pt ON pt.id = s.product_tmpl_id
             WHERE pp.id = s.product_id
               AND COALESCE(pp.alimac_gamma_code, '') = ''
               AND COALESCE(TRIM(pt.x_studio_codice_gamma), '') <> ''
            """
        )
        _logger.info("Codice Gamma dal modello (variante unica): %s varianti", cr.rowcount)

        cr.execute(
            """
            SELECT pt.id, pt.x_studio_codice_gamma
              FROM product_template pt
             WHERE COALESCE(TRIM(pt.x_studio_codice_gamma), '') <> ''
               AND (SELECT COUNT(*) FROM product_product pp
                     WHERE pp.product_tmpl_id = pt.id AND pp.active) > 1
            """
        )
        rows = cr.fetchall()
        if rows:
            _logger.warning(
                "Codice Gamma sul modello con più varianti, NON copiato (resta nel "
                "campo Studio x_studio_codice_gamma): %s",
                ", ".join(f"{tmpl_id}={code}" for tmpl_id, code in rows),
            )
    env.invalidate_all()


def _deactivate_studio(env):
    for model, xmlids in (("ir.ui.view", STUDIO_VIEWS), ("ir.ui.menu", STUDIO_MENUS)):
        for xmlid in xmlids:
            record = env.ref(STUDIO + xmlid, raise_if_not_found=False)
            if record and record._name == model and record.active:
                record.active = False
                _logger.info("Disattivato %s Studio: %s", model, record.display_name)


def post_init_hook(env):
    _migrate_gamma_code(env)
    _deactivate_studio(env)
