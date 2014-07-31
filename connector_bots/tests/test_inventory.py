# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2014 credativ Ltd
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp.tests.common as common
from openerp.osv import osv
from openerp.addons.connector.exception import JobError
from openerp import netsvc
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from .common import SetUpBotsBase
import json
from datetime import datetime

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

class TestInventory(SetUpBotsBase):

    maxDiff = None

    def test_00_create_inventory(self):
        """ Import a new inventory and validate """
        inventory_obj = self.registry('stock.inventory')
        bots_inventory_obj = self.registry('bots.stock.inventory')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        product = self.registry('product.product').browse(self.cr, self.uid, product_id, {'location': location_id, 'compute_child': False})

        # 1. Simulate importing inventory
        time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        conf = [{
            "inventory": {
                "partner": [{
                    "city": "",
                    "name": "Test Warehouse.",
                    "zip": "",
                    "country": "",
                    "street2": "",
                    "state": "",
                    "street1": "",
                }], 
                "inventory_line": [{
                    "product": 'M-Opt',
                    "qty_outgoing": "1", # FIXME: Unused for now
                    "datetime": time,
                    "qty_incoming": "1", # FIXME: Unused for now
                    "qty_outgoing_future": "1", # FIXME: Unused for now
                    "qty_available": "10",
                    "qty_outgoing_available": "0"
                }],
                "header": [{
                        "datetime": time,
                    }]
                }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.warehouse', 'inventory_%s.json', data)

        # 2. Create and run job to import inventory
        self.backend_model._scheduler_import_inventory(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock.import_stock_levels('bots.warehouse', %s, new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import inventory')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        product.refresh()
        print product.qty_available
        inventory_id = inventory_obj.search(self.cr, self.uid, [], order='create_date desc', limit=1)
        self.assertEquals(len(inventory_id), 1, 'A new inventory should be created for imported file')
        inventory = inventory_obj.browse(self.cr, self.uid, inventory_id[0])
        self.assertTrue(time in inventory.name, 'A new inventory should be created for imported file')
        self.assertEquals(inventory.state, 'done', 'Inventory should be done')
        self.assertEquals(product.qty_available, 10, 'Stock level should be 10')

        # 3. Import the same inventory and make sure a blank inventory is not created
        time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        conf = [{
            "inventory": {
                "partner": [{
                    "city": "",
                    "name": "Test Warehouse.",
                    "zip": "",
                    "country": "",
                    "street2": "",
                    "state": "",
                    "street1": "",
                }], 
                "inventory_line": [{
                    "product": 'M-Opt',
                    "qty_outgoing": "1", # FIXME: Unused for now
                    "datetime": time,
                    "qty_incoming": "1", # FIXME: Unused for now
                    "qty_outgoing_future": "1", # FIXME: Unused for now
                    "qty_available": "10",
                    "qty_outgoing_available": "0"
                }],
                "header": [{
                        "datetime": time,
                    }]
                }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.warehouse', 'inventory_%s.json', data)

        # 4. Create and run job to import inventory
        self.backend_model._scheduler_import_inventory(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock.import_stock_levels('bots.warehouse', %s, new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import inventory')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        product.refresh()
        print product.qty_available
        inventory_id = inventory_obj.search(self.cr, self.uid, [], order='create_date desc', limit=1)
        inventory = inventory_obj.browse(self.cr, self.uid, inventory_id[0]) # We should be browsing the previous inventory here
        self.assertTrue(time in inventory.name, 'A new inventory should not be created for imported file')
        self.assertEquals(product.qty_available, 10, 'Stock level should be 10')

    def test_01_create_inventory_wrong_product(self):
        """ Import a new inventory with an invalid product """
        inventory_obj = self.registry('stock.inventory')
        bots_inventory_obj = self.registry('bots.stock.inventory')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id

        # 1. Simulate importing inventory
        time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        conf = [{
            "inventory": {
                "partner": [{
                    "city": "",
                    "name": "Test Warehouse.",
                    "zip": "",
                    "country": "",
                    "street2": "",
                    "state": "",
                    "street1": "",
                }], 
                "inventory_line": [{
                    "product": 'PRODUCT DOES NOT EXIST',
                    "qty_outgoing": "1", # FIXME: Unused for now
                    "datetime": time,
                    "qty_incoming": "1", # FIXME: Unused for now
                    "qty_outgoing_future": "1", # FIXME: Unused for now
                    "qty_available": "10",
                    "qty_outgoing_available": "0"
                }],
                "header": [{
                        "datetime": time,
                    }]
                }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.warehouse', 'inventory_%s.json', data)

        # 2. Create and run job to import inventory - should fail
        self.backend_model._scheduler_import_inventory(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock.import_stock_levels('bots.warehouse', %s, new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import inventory')
        with self.assertRaises(JobError):
            res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])
