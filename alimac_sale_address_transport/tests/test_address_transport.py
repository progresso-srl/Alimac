# Copyright 2026 Progresso Srl
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAddressTransport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("account.group_delivery_invoice_address")
        cls.ton = cls.env.ref("uom.product_uom_ton")
        kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_sack = cls.env["uom.uom"].create(
            {"name": "Sacco 25kg", "relative_factor": 25, "relative_uom_id": kg.id}
        )
        cls.goods = cls.env["product.product"].create({
            "name": "Ciottolo Bianco Carrara 20-40",
            "type": "consu",
            "is_storable": True,
            "uom_id": cls.ton.id,
            "uom_ids": [Command.link(cls.uom_sack.id)],
            "list_price": 70.0,
        })
        cls.transport = cls.env["product.product"].create({
            "name": "Trasporto",
            "type": "service",
            "invoice_policy": "delivery",
            "list_price": 999.0,
        })
        cls.env.company.address_transport_product_id = cls.transport
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.goods, cls.warehouse.lot_stock_id, 1000.0
        )
        cls.customer = cls.env["res.partner"].create({"name": "Edilizia Rossi", "is_company": True})
        cls.addr_pisa = cls.env["res.partner"].create({
            "name": "Cantiere Pisa", "type": "delivery", "parent_id": cls.customer.id, "city": "Pisa",
        })
        cls.addr_lucca = cls.env["res.partner"].create({
            "name": "Cantiere Lucca", "type": "delivery", "parent_id": cls.customer.id, "city": "Lucca",
        })
        cls.addr_new = cls.env["res.partner"].create({
            "name": "Cantiere nuovo", "type": "delivery", "parent_id": cls.customer.id, "city": "Viareggio",
        })
        Rate = cls.env["sale.address.transport.rate"]
        cls.rate_pisa = Rate.create({"partner_id": cls.addr_pisa.id, "rate_type": "ton", "price": 25.0})
        cls.rate_lucca = Rate.create({"partner_id": cls.addr_lucca.id, "rate_type": "trip", "price": 450.0})

    def _order(self, address, qty=10.0, uom=None):
        return self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "partner_shipping_id": address.id,
            "order_line": [Command.create({
                "product_id": self.goods.id,
                "product_uom_qty": qty,
                "product_uom_id": (uom or self.ton).id,
            })],
        })

    def _transport_line(self, order):
        return order.order_line.filtered("is_address_transport")

    def test_ton_rate_creates_and_follows_quantities(self):
        order = self._order(self.addr_pisa)
        line = self._transport_line(order)
        self.assertEqual(order.address_transport_rate_id, self.rate_pisa)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_id, self.transport)
        self.assertEqual(line.product_uom_id, self.ton)
        self.assertAlmostEqual(line.product_uom_qty, 10.0)
        self.assertAlmostEqual(line.price_unit, 25.0)
        self.assertAlmostEqual(line.price_subtotal, 250.0)

        # Quantità merce cambiata: la riga trasporto segue, il prezzo resta la tariffa
        order.order_line.filtered(lambda l: not l.is_address_transport).product_uom_qty = 12.0
        self.assertAlmostEqual(line.product_uom_qty, 12.0)
        self.assertAlmostEqual(line.price_unit, 25.0)

        # Riga in sacchi: 40 × 25 kg = 1 t
        order.write({"order_line": [Command.create({
            "product_id": self.goods.id, "product_uom_qty": 40, "product_uom_id": self.uom_sack.id,
        })]})
        self.assertAlmostEqual(line.product_uom_qty, 13.0)
        self.assertEqual(len(self._transport_line(order)), 1)

    def test_update_prices_keeps_rate(self):
        order = self._order(self.addr_pisa)
        order.action_update_prices()
        self.assertAlmostEqual(self._transport_line(order).price_unit, 25.0)

    def test_trip_rate(self):
        order = self._order(self.addr_lucca)
        line = self._transport_line(order)
        self.assertEqual(order.address_transport_type, "trip")
        self.assertAlmostEqual(line.product_uom_qty, 1.0)
        self.assertAlmostEqual(line.price_subtotal, 450.0)
        order.address_transport_trips = 2
        self.assertAlmostEqual(line.price_subtotal, 900.0)

    def test_change_address_and_manual_price(self):
        order = self._order(self.addr_pisa)
        order.partner_shipping_id = self.addr_lucca
        line = self._transport_line(order)
        self.assertAlmostEqual(line.price_subtotal, 450.0)
        # Modifica manuale sull'ordine
        order.write({"address_transport_type": "ton", "address_transport_price": 30.0})
        self.assertAlmostEqual(line.product_uom_qty, 10.0)
        self.assertAlmostEqual(line.price_unit, 30.0)
        # La conferma non riporta la tariffa a quella dell'indirizzo
        order.action_confirm()
        self.assertAlmostEqual(line.price_unit, 30.0)

    def test_customer_address_is_ignored(self):
        """Indirizzo di consegna = cliente (non un contatto di tipo Consegna):
        niente campo, niente avviso, niente riga, anche con una tariffa scritta."""
        order = self._order(self.customer)
        self.assertFalse(order.address_transport_enabled)
        self.assertFalse(order.address_transport_missing)
        order.address_transport_price = 18.0
        self.assertFalse(self._transport_line(order))
        order.action_update_address_transport()
        self.assertFalse(self._transport_line(order))

    def test_delivery_address_without_rate_and_save(self):
        order = self._order(self.addr_new)
        self.assertTrue(order.address_transport_enabled)
        self.assertTrue(order.address_transport_missing)
        self.assertFalse(self._transport_line(order))
        order.address_transport_price = 18.0
        self.assertAlmostEqual(self._transport_line(order).price_subtotal, 180.0)
        order.action_save_address_transport_rate()
        self.assertAlmostEqual(self.addr_new.address_transport_rate_ids.price, 18.0)
        order2 = self._order(self.addr_new, qty=5.0)
        self.assertAlmostEqual(self._transport_line(order2).price_subtotal, 90.0)
        # Cambio da indirizzo di consegna a cliente: la riga sparisce
        order2.partner_shipping_id = self.customer
        self.assertFalse(self._transport_line(order2))

    def test_expired_rate_warns_and_save(self):
        yesterday = fields.Date.context_today(self.rate_pisa) - timedelta(days=1)
        self.rate_pisa.write({"date_from": yesterday - timedelta(days=30), "date_to": yesterday})
        order = self._order(self.addr_pisa)
        self.assertTrue(order.address_transport_enabled)
        self.assertTrue(order.address_transport_missing)
        self.assertFalse(self._transport_line(order))
        order.address_transport_price = 18.0
        self.assertAlmostEqual(self._transport_line(order).price_subtotal, 180.0)
        self.assertTrue(order.address_transport_can_save)
        order.action_save_address_transport_rate()
        new_rate = self.addr_pisa.address_transport_rate_ids - self.rate_pisa
        self.assertEqual(len(new_rate), 1)
        self.assertAlmostEqual(new_rate.price, 18.0)
        self.assertFalse(order.address_transport_can_save)
        order2 = self._order(self.addr_pisa, qty=5.0)
        self.assertAlmostEqual(self._transport_line(order2).price_subtotal, 90.0)

    def test_zero_price_removes_line(self):
        order = self._order(self.addr_pisa)
        order.address_transport_price = 0.0
        self.assertFalse(self._transport_line(order))

    def test_warehouse_rate_wins_and_validity(self):
        Rate = self.env["sale.address.transport.rate"]
        Rate.create({
            "partner_id": self.addr_pisa.id, "warehouse_id": self.warehouse.id,
            "rate_type": "ton", "price": 22.0,
        })
        order = self._order(self.addr_pisa)
        self.assertAlmostEqual(order.address_transport_price, 22.0)
        # Due tariffe generiche sovrapposte sullo stesso indirizzo: vietato
        with self.assertRaises(ValidationError):
            Rate.create({"partner_id": self.addr_pisa.id, "rate_type": "ton", "price": 27.0})
        # Tariffa scaduta: non si usa
        yesterday = fields.Date.context_today(Rate) - timedelta(days=1)
        self.rate_lucca.write({"date_from": yesterday - timedelta(days=30), "date_to": yesterday})
        order_lucca = self._order(self.addr_lucca)
        self.assertFalse(order_lucca.address_transport_rate_id)
        self.assertFalse(self._transport_line(order_lucca))

    def test_delivered_quantity_and_invoice(self):
        order = self._order(self.addr_pisa)
        order.action_confirm()
        line = self._transport_line(order)
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 6.0, "picked": True})
        Form.from_action(self.env, picking.button_validate()).save().process()  # backorder
        self.assertAlmostEqual(line.qty_delivered, 6.0)
        invoice = order._create_invoices()
        transport_inv_line = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.transport)
        self.assertAlmostEqual(transport_inv_line.quantity, 6.0)
        self.assertAlmostEqual(transport_inv_line.price_unit, 25.0)

    def test_confirmed_order_qty_zero_instead_of_unlink(self):
        order = self._order(self.addr_pisa)
        order.action_confirm()
        order.address_transport_price = 0.0
        line = self._transport_line(order)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_qty, 0.0)

    def test_form_flow(self):
        with Form(self.env["sale.order"]) as so:
            so.partner_id = self.customer
            so.partner_shipping_id = self.addr_pisa
            with so.order_line.new() as ol:
                ol.product_id = self.goods
                ol.product_uom_qty = 8.0
        order = so.record
        self.assertAlmostEqual(self._transport_line(order).price_subtotal, 200.0)
