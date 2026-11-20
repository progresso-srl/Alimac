# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged("post_install", "-at_install")
class TestAlimacFormatWizard(TestMrpCommon):
    """Flusso completo con le rotte create dal wizard, da ordine di vendita a consegna."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_tracking_lot")
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_multi_locations")
        cls.env.user.group_ids += cls.env.ref("stock.group_adv_location")
        cls.wh = cls.warehouse_1
        kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_sack = cls.env["uom.uom"].create(
            {"name": "Sacco 25kg", "relative_factor": 25, "relative_uom_id": kg.id}
        )
        cls.package_type = cls.env["stock.package.type"].create({"name": "Pallet 1500kg"})
        cls.uom_pallet = cls.env["uom.uom"].create(
            {
                "name": "Pallet 1500kg - 25kg x 60",
                "relative_factor": 60,
                "relative_uom_id": cls.uom_sack.id,
                "package_type_id": cls.package_type.id,
            }
        )
        cls.confezionato = cls.env["stock.location"].create(
            {"name": "Confezionato", "location_id": cls.wh.view_location_id.id, "usage": "internal"}
        )
        cls.sfuso = cls.env["product.product"].create(
            {"name": "Granulato sfuso", "is_storable": True, "uom_id": kg.id}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Granulato confezionato",
                "is_storable": True,
                "uom_id": kg.id,
                "uom_ids": [Command.set([cls.uom_sack.id, cls.uom_pallet.id])],
            }
        )
        cls.pedana = cls.env["product.product"].create({"name": "Pedana", "is_storable": True})
        cls.env["alimac.package.type.material"].create(
            {"package_type_id": cls.package_type.id, "product_id": cls.pedana.id, "quantity": 1}
        )
        cls.prelievo_type = cls.env["stock.picking.type"].create(
            {
                "name": "Prelievo confezionato",
                "code": "internal",
                "sequence_code": "PCONF",
                "warehouse_id": cls.wh.id,
                "default_location_src_id": cls.confezionato.id,
                "default_location_dest_id": cls.confezionato.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente"})

    def _run_wizard(self, format_type, uom):
        wizard = self.env["alimac.packaging.format.wizard"].create(
            {
                "format_type": format_type,
                "warehouse_id": self.wh.id,
                "uom_id": uom.id,
                "prelievo_type_id": self.prelievo_type.id,
            }
        )
        self.assertEqual(wizard.parent_location_id, self.confezionato)
        action = wizard.action_configure()
        return wizard, self.env["stock.route"].browse(action["res_id"])

    def _configure(self):
        wizard_sack, route_sack = self._run_wizard("production", self.uom_sack)
        wizard_pallet, route_pallet = self._run_wizard("pallet", self.uom_pallet)
        sack_location = wizard_sack.existing_location_id or self.env["stock.location"].search(
            [("alimac_count_uom_id", "=", self.uom_sack.id)]
        )
        production_type = self.env["stock.picking.type"].search(
            [("code", "=", "mrp_operation"), ("default_location_dest_id", "=", sack_location.id)]
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom_id": self.uom_sack.id,
                "picking_type_id": production_type.id,
                "bom_line_ids": [Command.create(
                    {"product_id": self.sfuso.id, "product_qty": 25, "product_uom_id": self.sfuso.uom_id.id}
                )],
            }
        )
        return route_sack, route_pallet, sack_location, production_type

    def _order(self, route, uom, qty):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [Command.create({
                    "product_id": self.product.id,
                    "product_uom_qty": qty,
                    "product_uom_id": uom.id,
                    "route_ids": [Command.set(route.ids)],
                })],
            }
        )
        order.action_confirm()
        return order

    def _mo(self, order):
        return self.env["mrp.production"].search([("product_id", "=", self.product.id), ("state", "=", "confirmed")])

    def _finish(self, mo, qty_uom_units):
        with Form(mo) as mo_form:
            mo_form.qty_producing = qty_uom_units
        mo.with_context(skip_backorder=True).button_mark_done()
        self.assertEqual(mo.state, "done")

    def test_01_wizard_creates_configuration(self):
        route_sack, route_pallet, sack_location, production_type = self._configure()
        self.assertEqual(len(route_sack.rule_ids), 3)
        self.assertEqual(len(route_pallet.rule_ids), 4)
        self.assertTrue(route_pallet.sale_selectable)
        self.assertEqual(sack_location.location_id, self.confezionato)
        self.assertEqual(production_type.default_location_src_id, self.wh.lot_stock_id)
        packing_type = route_pallet.rule_ids.picking_type_id.filtered("alimac_is_pallet_packing")
        self.assertTrue(packing_type)
        self.assertEqual(packing_type.default_location_src_id, sack_location)
        self.assertTrue(packing_type.alimac_consumption_location_id)
        self.assertTrue(self.prelievo_type.alimac_auto_validate)
        self.assertTrue(all(route_pallet.rule_ids.mapped("location_dest_from_rule")))

        # Rilancio: riusa tutto, nessun duplicato.
        locations_before = self.env["stock.location"].search_count([])
        types_before = self.env["stock.picking.type"].search_count([])
        _wizard, route_again = self._run_wizard("pallet", self.uom_pallet)
        self.assertEqual(route_again, route_pallet)
        self.assertEqual(self.env["stock.location"].search_count([]), locations_before)
        self.assertEqual(self.env["stock.picking.type"].search_count([]), types_before)

    def test_02_full_pallet_flow(self):
        """Ordine 2 pallet 25x60: MO 120 sacchi, ne produco 130, Imballa, consegna pronta."""
        _route_sack, route_pallet, sack_location, _ptype = self._configure()
        order = self._order(route_pallet, self.uom_pallet, 2)
        mo = self._mo(order)
        self.assertEqual(len(mo), 1)
        self.assertEqual(mo.product_uom_id, self.uom_sack)
        self.assertAlmostEqual(mo.product_qty, 120)
        self.assertEqual(mo.alimac_sale_uom_id, self.uom_pallet)
        self.assertAlmostEqual(mo.alimac_sale_uom_qty, 2)
        self.assertEqual(mo.alimac_sale_packaging_summary, "2 Pallet 1500kg - 25kg x 60")
        self.assertFalse(mo.alimac_packaging_mismatch)
        self.assertEqual(mo.location_dest_id, sack_location)

        self._finish(mo, 130)
        wizard = self.env["alimac.pallet.packing.wizard"].with_context(
            default_production_id=mo.id
        ).create({})
        self.assertTrue(wizard.picking_id)
        self.assertEqual(wizard.package_count, 2)
        wizard.action_pack()

        pickings = order.picking_ids
        delivery = pickings.filtered(lambda p: p.picking_type_id == self.wh.out_type_id)
        others = pickings - delivery
        self.assertTrue(all(p.state == "done" for p in others), others.mapped("state"))
        self.assertEqual(delivery.state, "assigned")
        self.assertEqual(len(delivery.move_line_ids.package_id), 2)
        quants = self.env["stock.quant"].search(
            [("location_id", "=", sack_location.id), ("product_id", "=", self.product.id)]
        )
        self.assertAlmostEqual(sum(quants.mapped("alimac_count_qty")), 10)
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")
        self.assertAlmostEqual(order.order_line.qty_delivered, 2)

    def test_03_full_sack_flow(self):
        """Ordine 3 sacchi 25 kg: MO, prelievo automatico, consegna pronta."""
        route_sack, _route_pallet, _loc, _ptype = self._configure()
        order = self._order(route_sack, self.uom_sack, 3)
        mo = self._mo(order)
        self.assertAlmostEqual(mo.product_qty, 3)
        self._finish(mo, 3)
        delivery = order.picking_ids.filtered(lambda p: p.picking_type_id == self.wh.out_type_id)
        prelievo = order.picking_ids - delivery
        self.assertEqual(prelievo.state, "done")
        self.assertEqual(delivery.state, "assigned")

    def test_05_mixed_order_pallet_and_sacks(self):
        """Stesso prodotto: 2 pallet 25x60 + 3 sacchi 25 kg nello stesso ordine."""
        route_sack, route_pallet, sack_location, _ptype = self._configure()
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [
                    Command.create({
                        "product_id": self.product.id,
                        "product_uom_qty": 2,
                        "product_uom_id": self.uom_pallet.id,
                        "route_ids": [Command.set(route_pallet.ids)],
                    }),
                    Command.create({
                        "product_id": self.product.id,
                        "product_uom_qty": 3,
                        "product_uom_id": self.uom_sack.id,
                        "route_ids": [Command.set(route_sack.ids)],
                    }),
                ],
            }
        )
        order.action_confirm()
        mos = self._mo(order)
        self.assertAlmostEqual(sum(mos.mapped("product_qty")), 123)
        if len(mos) == 1:  # Odoo 19 unisce le due richieste nello stesso MO
            self.assertEqual(
                mos.alimac_sale_packaging_summary,
                "2 Pallet 1500kg - 25kg x 60 + 3 Sacco 25kg",
            )
            self.assertFalse(mos.alimac_packaging_mismatch)
        for mo in mos:
            self._finish(mo, mo.product_qty)
        pallet_mo = mos.filtered(lambda m: m.alimac_packing_picking_ids)
        self.assertEqual(len(pallet_mo), 1 if len(mos) == 2 else len(mos))
        wizard = self.env["alimac.pallet.packing.wizard"].with_context(
            default_production_id=pallet_mo[:1].id
        ).create({})
        self.assertAlmostEqual(wizard.qty_to_pack, 120)
        self.assertEqual(wizard.package_count, 2)
        wizard.action_pack()
        delivery = order.picking_ids.filtered(lambda p: p.picking_type_id == self.wh.out_type_id)
        self.assertEqual(len(delivery), 1, "Un solo WH/OUT per i due formati")
        others = order.picking_ids - delivery
        self.assertTrue(all(p.state == "done" for p in others), others.mapped("state"))
        self.assertEqual(delivery.state, "assigned")
        self.assertAlmostEqual(sum(delivery.move_ids.mapped("product_uom_qty")), 3075)

    def test_06_missing_bom_for_format_warning(self):
        """Pallet 25x60 + Sacco 10kg senza distinta 10 kg: avviso solo sul 10 kg."""
        kg = self.env.ref("uom.product_uom_kgm")
        uom_sack_10 = self.env["uom.uom"].create(
            {"name": "Sacco 10kg", "relative_factor": 10, "relative_uom_id": kg.id}
        )
        self.product.uom_ids = [Command.link(uom_sack_10.id)]
        _route_sack, route_pallet, _loc, _ptype = self._configure()
        _wizard, route_sack_10 = self._run_wizard("production", uom_sack_10)

        def confirm_order():
            order = self.env["sale.order"].create(
                {
                    "partner_id": self.partner.id,
                    "warehouse_id": self.wh.id,
                    "order_line": [
                        Command.create({
                            "product_id": self.product.id,
                            "product_uom_qty": 2,
                            "product_uom_id": self.uom_pallet.id,
                            "route_ids": [Command.set(route_pallet.ids)],
                        }),
                        Command.create({
                            "product_id": self.product.id,
                            "product_uom_qty": 2,
                            "product_uom_id": uom_sack_10.id,
                            "route_ids": [Command.set(route_sack_10.ids)],
                        }),
                    ],
                }
            )
            order.action_confirm()
            return order.picking_ids.move_ids.reference_ids.mapped("move_ids").production_id | \
                self.env["mrp.production"].search([("origin", "=", order.name)])

        mos = confirm_order()
        # Senza distinta 10 kg Odoo usa quella da 25 kg: l'MO del 10 kg esce in
        # Sacco 25kg (0,8 sacchi) e mostra l'avviso; quello dei pallet no.
        pallet_mo = mos.filtered(lambda m: "Pallet" in (m.alimac_sale_packaging_summary or ""))
        sack_10_mo = mos - pallet_mo
        self.assertEqual(len(pallet_mo), 1)
        self.assertEqual(len(sack_10_mo), 1)
        self.assertEqual(pallet_mo.alimac_sale_packaging_summary, "2 Pallet 1500kg - 25kg x 60")
        self.assertFalse(pallet_mo.alimac_packaging_mismatch)
        self.assertEqual(sack_10_mo.product_uom_id, self.uom_sack)
        self.assertEqual(sack_10_mo.alimac_sale_packaging_summary, "2 Sacco 10kg")
        self.assertTrue(sack_10_mo.alimac_packaging_mismatch)
        self.assertEqual(sack_10_mo.alimac_packaging_mismatch_lines, "2 Sacco 10kg")

        # Creata la distinta 10 kg: MO separati, nessun avviso.
        sack_10_type = route_sack_10.rule_ids.filtered(lambda r: r.action == "manufacture").picking_type_id
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom_id": uom_sack_10.id,
                "picking_type_id": sack_10_type.id,
                "bom_line_ids": [Command.create(
                    {"product_id": self.sfuso.id, "product_qty": 10, "product_uom_id": kg.id}
                )],
            }
        )
        mos = confirm_order()
        self.assertEqual(len(mos), 2)
        for mo in mos:
            self.assertFalse(mo.alimac_packaging_mismatch, mo.alimac_sale_packaging_summary)
        self.assertEqual(
            sorted(mos.mapped("alimac_sale_packaging_summary")),
            ["2 Pallet 1500kg - 25kg x 60", "2 Sacco 10kg"],
        )

    def test_07_mto_ignores_stock(self):
        """Su ordine (default): con 30 sacchi a stock l'MO produce comunque tutti i 120."""
        _route_sack, route_pallet, sack_location, _ptype = self._configure()
        self.env["stock.quant"]._update_available_quantity(self.product, sack_location, 750)
        self.assertEqual(
            set(route_pallet.rule_ids.filtered(lambda r: r.action == "pull").mapped("procure_method")),
            {"make_to_order"},
        )
        order = self._order(route_pallet, self.uom_pallet, 2)
        mo = self._mo(order)
        self.assertAlmostEqual(mo.product_qty, 120)
        self.assertEqual(mo.alimac_sale_packaging_summary, "2 Pallet 1500kg - 25kg x 60")

    def test_08_route_from_uom(self):
        """Il wizard collega la rotta all'unità: la riga d'ordine la propone da sola."""
        route_sack, route_pallet, _loc, _ptype = self._configure()
        self.assertEqual(self.uom_pallet.alimac_route_ids, route_pallet)
        self.assertEqual(self.uom_sack.alimac_route_ids, route_sack)
        self.assertTrue(route_pallet.alimac_uom_selectable)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [Command.create({
                    "product_id": self.product.id,
                    "product_uom_qty": 2,
                    "product_uom_id": self.uom_pallet.id,
                })],
            }
        )
        line = order.order_line
        self.assertEqual(line.route_ids, route_pallet)
        # Cambio unità: cambia la rotta.
        line.product_uom_id = self.uom_sack
        self.assertEqual(line.route_ids, route_sack)
        line.product_uom_id = self.uom_pallet
        order.action_confirm()
        mo = self._mo(order)
        self.assertAlmostEqual(mo.product_qty, 120)
        self.assertEqual(mo.state, "confirmed")

    def test_09_fallback_bom_keeps_mo_draft(self):
        """Formato senza distinta: MO in bozza; creata la distinta, il pulsante la applica."""
        kg = self.env.ref("uom.product_uom_kgm")
        uom_sack_10 = self.env["uom.uom"].create(
            {"name": "Sacco 10kg", "relative_factor": 10, "relative_uom_id": kg.id}
        )
        self.product.uom_ids = [Command.link(uom_sack_10.id)]
        self._configure()
        _wizard, route_sack_10 = self._run_wizard("production", uom_sack_10)
        order = self._order(route_sack_10, uom_sack_10, 3)
        mo = self.env["mrp.production"].search(
            [("product_id", "=", self.product.id), ("state", "=", "draft")]
        )
        self.assertEqual(len(mo), 1)
        self.assertTrue(mo.alimac_is_format_fallback)
        self.assertEqual(mo.product_uom_id, self.uom_sack)  # distinta da 25 kg
        with self.assertRaises(UserError):
            mo.action_alimac_apply_format_bom()

        sack_10_type = mo.alimac_format_picking_type_id
        bom_10 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom_id": uom_sack_10.id,
                "picking_type_id": sack_10_type.id,
                "bom_line_ids": [Command.create(
                    {"product_id": self.sfuso.id, "product_qty": 10, "product_uom_id": kg.id}
                )],
            }
        )
        location_dest = mo.location_dest_id
        mo.action_alimac_apply_format_bom()
        self.assertEqual(mo.bom_id, bom_10)
        self.assertEqual(mo.product_uom_id, uom_sack_10)
        self.assertAlmostEqual(mo.product_qty, 3)
        self.assertEqual(mo.picking_type_id, sack_10_type)
        self.assertEqual(mo.location_dest_id, location_dest)
        self.assertFalse(mo.alimac_is_format_fallback)
        self.assertAlmostEqual(sum(mo.move_raw_ids.mapped("product_uom_qty")), 30)
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        self._finish(mo, 3)
        delivery = order.picking_ids.filtered(lambda p: p.picking_type_id == self.wh.out_type_id)
        self.assertEqual(delivery.state, "assigned")

    def test_04_install_creates_consumption_location(self):
        location = self.env["stock.location"]._alimac_get_consumption_location()
        self.assertTrue(location)
        self.assertEqual(location.usage, "production")
        self.assertFalse(location.location_id)
