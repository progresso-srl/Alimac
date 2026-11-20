# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged("post_install", "-at_install")
class TestAlimacPalletPacking(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_tracking_lot")
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_multi_locations")
        kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_sack = cls.env["uom.uom"].create(
            {"name": "Sacco 20kg", "relative_factor": 20, "relative_uom_id": kg.id}
        )
        cls.package_type = cls.env["stock.package.type"].create({"name": "Pallet 1500kg"})
        cls.uom_pallet = cls.env["uom.uom"].create(
            {
                "name": "Pallet 1500kg - 20kg x 75",
                "relative_factor": 75,
                "relative_uom_id": cls.uom_sack.id,
                "package_type_id": cls.package_type.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Granulato Nero Assoluto confezionato",
                "is_storable": True,
                "uom_id": kg.id,
                "uom_ids": [Command.set([cls.uom_sack.id, cls.uom_pallet.id])],
            }
        )
        cls.pedana = cls.env["product.product"].create(
            {"name": "Pedana 100x100", "is_storable": True}
        )
        cls.film = cls.env["product.product"].create(
            {"name": "Film estensibile", "is_storable": True, "uom_id": kg.id}
        )
        cls.env["alimac.package.type.material"].create(
            [
                {"package_type_id": cls.package_type.id, "product_id": cls.pedana.id, "quantity": 1},
                {"package_type_id": cls.package_type.id, "product_id": cls.film.id, "quantity": 0.4},
            ]
        )
        stock = cls.warehouse_1.lot_stock_id
        cls.loc_sacks = cls.env["stock.location"].create(
            {"name": "Sacco20kg", "location_id": stock.id, "usage": "internal"}
        )
        cls.loc_pallet = cls.env["stock.location"].create(
            {"name": "Pallet 1500 - 20x75", "location_id": stock.id, "usage": "internal"}
        )
        cls.loc_consumption = cls.env["stock.location"].create(
            {"name": "Consumo imballi", "usage": "inventory"}
        )
        cls.packing_type = cls.env["stock.picking.type"].create(
            {
                "name": "Imballo 20x75",
                "code": "internal",
                "sequence_code": "IMB",
                "warehouse_id": cls.warehouse_1.id,
                "default_location_src_id": cls.loc_sacks.id,
                "default_location_dest_id": cls.loc_pallet.id,
                "alimac_is_pallet_packing": True,
                "alimac_material_location_id": stock.id,
                "alimac_consumption_location_id": cls.loc_consumption.id,
            }
        )
        cls.manu_type = cls.warehouse_1.manu_type_id
        cls.manu_type.default_location_dest_id = cls.loc_sacks

    def _produce(self, planned_qty_kg, produced_qty_kg, move_dest=None):
        vals = {
            "product_id": self.product.id,
            "product_qty": planned_qty_kg,
            "product_uom_id": self.product.uom_id.id,
            "picking_type_id": self.manu_type.id,
            "location_dest_id": self.loc_sacks.id,
        }
        if move_dest:
            vals["move_dest_ids"] = [Command.link(move_dest.id)]
        mo = self.env["mrp.production"].create(vals)
        mo.action_confirm()
        with Form(mo) as mo_form:
            mo_form.qty_producing = produced_qty_kg
        mo.with_context(skip_backorder=True).button_mark_done()
        self.assertEqual(mo.state, "done")
        return mo

    def _open_wizard(self, mo):
        action = mo.action_alimac_open_pallet_packing()
        return (
            self.env[action["res_model"]]
            .with_context(action["context"])
            .create({})
        )

    def _qty(self, location, product, package=False):
        domain = [("location_id", "=", location.id), ("product_id", "=", product.id)]
        if package is not False:
            domain.append(("package_id", "=", package))
        return sum(self.env["stock.quant"].search(domain).mapped("quantity"))

    def test_01_linked_packing_overproduction(self):
        """Ordine 2 pallet (3000 kg), produco 160 sacchi: 2 colli, 10 sacchi restano."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.packing_type.id,
                "location_id": self.loc_sacks.id,
                "location_dest_id": self.loc_pallet.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom": self.product.uom_id.id,
                            "product_uom_qty": 3000,
                            "location_id": self.loc_sacks.id,
                            "location_dest_id": self.loc_pallet.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        mo = self._produce(3000, 3200, move_dest=picking.move_ids)

        wizard = self._open_wizard(mo)
        self.assertEqual(wizard.picking_id, picking)
        self.assertEqual(wizard.packaging_uom_id, self.uom_pallet)
        self.assertEqual(wizard.content_uom_id, self.uom_sack)
        self.assertAlmostEqual(wizard.qty_per_package, 75)
        self.assertAlmostEqual(wizard.qty_to_pack, 150)
        self.assertEqual(wizard.package_count, 2)
        self.assertEqual(len(wizard.material_line_ids), 2)
        wizard.action_pack()

        self.assertEqual(picking.state, "done")
        self.assertEqual(len(picking.move_ids), 1)
        packages = picking.move_line_ids.result_package_id
        self.assertEqual(len(packages), 2)
        self.assertEqual(packages.package_type_id, self.package_type)
        for package in packages:
            self.assertAlmostEqual(self._qty(self.loc_pallet, self.product, package.id), 1500)
        self.assertAlmostEqual(self._qty(self.loc_sacks, self.product), 200)
        stock = self.warehouse_1.lot_stock_id
        self.assertAlmostEqual(self._qty(stock, self.pedana), -2)
        self.assertAlmostEqual(self._qty(stock, self.film), -0.8)
        self.assertEqual(len(picking.alimac_material_move_ids), 2)
        self.assertEqual(mo.alimac_packing_picking_ids, picking)

        quants = self.env["stock.quant"].search(
            [("location_id", "=", self.loc_pallet.id), ("product_id", "=", self.product.id)]
        )
        self.assertEqual(sum(quants.mapped("alimac_package_count")), 2)
        self.assertEqual(quants.alimac_package_type_id, self.package_type)

    def test_02_stock_production_full_packages_only(self):
        """MO per magazzino da 160 sacchi: crea l'imballo con 2 pallet, 10 sacchi restano."""
        mo = self._produce(3200, 3200)
        wizard = self._open_wizard(mo)
        self.assertFalse(wizard.picking_id)
        self.assertEqual(wizard.picking_type_id, self.packing_type)
        self.assertAlmostEqual(wizard.qty_available, 160)
        self.assertAlmostEqual(wizard.qty_to_pack, 150)
        self.assertEqual(wizard.package_count, 2)
        wizard.action_pack()

        picking = mo.alimac_packing_picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.state, "done")
        self.assertEqual(len(picking.move_line_ids.result_package_id), 2)
        self.assertAlmostEqual(self._qty(self.loc_sacks, self.product), 200)
        self.assertAlmostEqual(self._qty(self.loc_pallet, self.product), 3000)

    def test_03_custom_package_size(self):
        """30 sacchi in 2 pallet da 15."""
        mo = self._produce(600, 600)
        wizard = self._open_wizard(mo)
        wizard.qty_per_package = 15
        wizard.qty_to_pack = 30
        self.assertEqual(wizard.package_count, 2)
        self.assertEqual(wizard.material_line_ids.filtered(
            lambda l: l.product_id == self.pedana).quantity, 2)
        wizard.action_pack()
        picking = mo.alimac_packing_picking_ids
        packages = picking.move_line_ids.result_package_id
        self.assertEqual(len(packages), 2)
        for package in packages:
            self.assertAlmostEqual(self._qty(self.loc_pallet, self.product, package.id), 300)

    def test_04_partial_packing_creates_backorder(self):
        """Ordine 2 pallet, ne imballo solo 1: l'Imballo va in backorder per il secondo."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.packing_type.id,
                "location_id": self.loc_sacks.id,
                "location_dest_id": self.loc_pallet.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom": self.product.uom_id.id,
                            "product_uom_qty": 3000,
                            "location_id": self.loc_sacks.id,
                            "location_dest_id": self.loc_pallet.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        mo = self._produce(3000, 3000, move_dest=picking.move_ids)
        wizard = self._open_wizard(mo)
        self.assertAlmostEqual(wizard.qty_to_pack, 150)
        wizard.qty_to_pack = 75
        self.assertEqual(wizard.package_count, 1)
        wizard.action_pack()
        self.assertEqual(picking.state, "done")
        self.assertAlmostEqual(picking.move_ids.quantity, 1500)
        backorder = self.env["stock.picking"].search([("backorder_id", "=", picking.id)])
        self.assertEqual(len(backorder), 1)
        self.assertAlmostEqual(backorder.move_ids.product_uom_qty, 1500)
        self.assertAlmostEqual(self._qty(self.loc_sacks, self.product), 1500)
        stock = self.warehouse_1.lot_stock_id
        self.assertAlmostEqual(self._qty(stock, self.pedana), -1)

        # Secondo giro: il pulsante trova il backorder e imballa il secondo pallet.
        wizard = self._open_wizard(mo)
        self.assertEqual(wizard.picking_id, backorder)
        self.assertAlmostEqual(wizard.qty_to_pack, 75)
        wizard.action_pack()
        self.assertEqual(backorder.state, "done")
        self.assertAlmostEqual(self._qty(self.loc_pallet, self.product), 3000)
        self.assertAlmostEqual(self._qty(stock, self.pedana), -2)

    def test_06_underproduction_backorder(self):
        """Ordine 2 pallet, la macchina fa solo 140 sacchi: colli 75 + 65, 10 sacchi in backorder."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.packing_type.id,
                "location_id": self.loc_sacks.id,
                "location_dest_id": self.loc_pallet.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom": self.product.uom_id.id,
                            "product_uom_qty": 3000,
                            "location_id": self.loc_sacks.id,
                            "location_dest_id": self.loc_pallet.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        mo = self._produce(3000, 2800, move_dest=picking.move_ids)
        wizard = self._open_wizard(mo)
        self.assertAlmostEqual(wizard.qty_to_pack, 140)
        self.assertEqual(wizard.package_count, 2)
        self.assertAlmostEqual(wizard.last_package_qty, 65)
        wizard.action_pack()
        self.assertEqual(picking.state, "done")
        self.assertEqual(len(picking.move_ids), 1)
        backorder = self.env["stock.picking"].search([("backorder_id", "=", picking.id)])
        self.assertEqual(len(backorder), 1)
        self.assertAlmostEqual(backorder.move_ids.product_uom_qty, 200)

    def _chain_imballo_prelievo(self, qty):
        """Catena Imballo -> Prelievo come nella rotta pallet."""
        self.loc_out = self.env["stock.location"].create(
            {"name": "Confezionato uscita", "location_id": self.warehouse_1.lot_stock_id.id,
             "usage": "internal"}
        )
        self.prelievo_type = self.env["stock.picking.type"].create(
            {
                "name": "Prelievo confezionato",
                "code": "internal",
                "sequence_code": "PCONF",
                "warehouse_id": self.warehouse_1.id,
                "default_location_src_id": self.loc_pallet.id,
                "default_location_dest_id": self.loc_out.id,
                "alimac_auto_validate": True,
            }
        )
        prelievo = self.env["stock.picking"].create(
            {
                "picking_type_id": self.prelievo_type.id,
                "location_id": self.loc_pallet.id,
                "location_dest_id": self.loc_out.id,
                "move_ids": [Command.create({
                    "product_id": self.product.id,
                    "product_uom": self.product.uom_id.id,
                    "product_uom_qty": qty,
                    "location_id": self.loc_pallet.id,
                    "location_dest_id": self.loc_out.id,
                    "procure_method": "make_to_order",
                })],
            }
        )
        imballo = self.env["stock.picking"].create(
            {
                "picking_type_id": self.packing_type.id,
                "location_id": self.loc_sacks.id,
                "location_dest_id": self.loc_pallet.id,
                "move_ids": [Command.create({
                    "product_id": self.product.id,
                    "product_uom": self.product.uom_id.id,
                    "product_uom_qty": qty,
                    "location_id": self.loc_sacks.id,
                    "location_dest_id": self.loc_pallet.id,
                    "move_dest_ids": [Command.link(prelievo.move_ids.id)],
                })],
            }
        )
        imballo.action_confirm()
        prelievo.action_confirm()
        return imballo, prelievo

    def test_07_auto_validate_prelievo_after_packing(self):
        """Dopo Imballa, il prelievo con Convalida automatica si chiude da solo coi colli."""
        imballo, prelievo = self._chain_imballo_prelievo(3000)
        mo = self._produce(3000, 3200, move_dest=imballo.move_ids)
        # L'MO chiuso non deve convalidare l'imballo (non ha il flag).
        self.assertNotEqual(imballo.state, "done")
        self._open_wizard(mo).action_pack()
        self.assertEqual(imballo.state, "done")
        self.assertEqual(prelievo.state, "done")
        quants = self.env["stock.quant"].search(
            [("location_id", "=", self.loc_out.id), ("product_id", "=", self.product.id)]
        )
        self.assertAlmostEqual(sum(quants.mapped("quantity")), 3000)
        self.assertEqual(len(quants.package_id), 2, "I colli devono seguire la merce")
        self.assertEqual(sum(quants.mapped("alimac_package_count")), 2)

    def test_08_auto_validate_after_production(self):
        """Rotta sacchi: MO -> Prelievo con Convalida automatica (ex regola Studio)."""
        self.loc_out = self.env["stock.location"].create(
            {"name": "Uscita", "location_id": self.warehouse_1.lot_stock_id.id, "usage": "internal"}
        )
        prelievo_type = self.env["stock.picking.type"].create(
            {
                "name": "Prelievo confezionato",
                "code": "internal",
                "sequence_code": "PCONF",
                "warehouse_id": self.warehouse_1.id,
                "default_location_src_id": self.loc_sacks.id,
                "default_location_dest_id": self.loc_out.id,
                "alimac_auto_validate": True,
            }
        )
        prelievo = self.env["stock.picking"].create(
            {
                "picking_type_id": prelievo_type.id,
                "location_id": self.loc_sacks.id,
                "location_dest_id": self.loc_out.id,
                "move_ids": [Command.create({
                    "product_id": self.product.id,
                    "product_uom": self.product.uom_id.id,
                    "product_uom_qty": 600,
                    "location_id": self.loc_sacks.id,
                    "location_dest_id": self.loc_out.id,
                })],
            }
        )
        prelievo.action_confirm()
        self._produce(600, 600, move_dest=prelievo.move_ids)
        self.assertEqual(prelievo.state, "done")

    def test_09_count_qty_by_location_unit(self):
        """Colonna N: giacenza nell'unità di conteggio dell'ubicazione."""
        self.loc_sacks.alimac_count_uom_id = self.uom_sack
        self._produce(600, 600)
        quants = self.env["stock.quant"].search(
            [("location_id", "=", self.loc_sacks.id), ("product_id", "=", self.product.id)]
        )
        self.assertAlmostEqual(sum(quants.mapped("alimac_count_qty")), 30)

    def test_10_studio_migration_hook(self):
        """La migrazione attiva il flag sui Prelievo confezionato."""
        from odoo.addons.alimac_mrp_imballo_pallet.hooks import post_init_hook

        picking_type = self.env["stock.picking.type"].create(
            {
                "name": "Prelievo confezionato",
                "code": "internal",
                "sequence_code": "PC2",
                "warehouse_id": self.warehouse_1.id,
                "default_location_src_id": self.loc_pallet.id,
                "default_location_dest_id": self.loc_sacks.id,
            }
        )
        # Simula la tabella del campo Studio x_studio_imballo_1.
        self.env.cr.execute(
            "CREATE TABLE IF NOT EXISTS x_stock_location_uom_uom_rel "
            "(stock_location_id integer, uom_uom_id integer)"
        )
        self.env.cr.execute(
            "INSERT INTO x_stock_location_uom_uom_rel VALUES (%s, %s)",
            (self.loc_sacks.id, self.uom_sack.id),
        )
        post_init_hook(self.env)
        self.assertTrue(picking_type.alimac_auto_validate)
        self.assertEqual(self.loc_sacks.alimac_count_uom_id, self.uom_sack)

    def test_05_requires_done_production(self):
        mo = self.env["mrp.production"].create(
            {"product_id": self.product.id, "product_qty": 1500, "picking_type_id": self.manu_type.id}
        )
        mo.action_confirm()
        wizard = self.env["alimac.pallet.packing.wizard"].create({"production_id": mo.id})
        with self.assertRaises(UserError):
            wizard.action_pack()
