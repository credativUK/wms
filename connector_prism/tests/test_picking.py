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

from .common import SetUpBotsBase
import json

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

class TestPicking(SetUpBotsBase):

    maxDiff = None

    def _create_picking(self, picking_dict):
        picking_obj = self.registry('stock.picking')
        picking_id = picking_obj.create(self.cr, self.uid, picking_dict)
        picking = picking_obj.browse(self.cr, self.uid, picking_id)
        return picking

    def _assign_picking(self, picking):
        picking_obj = self.registry('stock.picking')
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_confirm', self.cr)
        picking_obj.force_assign(self.cr, self.uid, [picking.id,])
        return True

    def _create_and_assign_picking(self, picking_dict):
        picking = self._create_picking(picking_dict)
        self._assign_picking(picking)
        return picking

class TestPickingOut(TestPicking):

    def test_00_create_picking(self):
        """ Create a new picking and test an export job is created on assignment """
        picking_obj = self.registry('stock.picking')
        bots_picking_out_obj = self.registry('bots.stock.picking.out')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id
        location_dest_id = self.get_ref('stock', 'stock_location_customers')[1]
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKOUT_001',
                'partner_id': partner_id,
                'name': 'BT_PICKOUT_001',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'out',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 1,
                        'name': 'BT_PICKOUT_001/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_out_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.out', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.out', '^picking_out_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'out'}],
              u'pickings': [{u'id': u'BTPICKOUT001',
                             u'line': [{u'id': u'BTPICKOUT001S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 1,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKOUT001',
                             u'order': u'BTPICKOUT001',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'out'}]}},
            'Output file has unexpected content')

    def test_01_create_picking_and_cancel(self):
        """ Create a new picking and test an export job is created on assignment, then try to cancel before and after export """
        picking_obj = self.registry('stock.picking')
        bots_picking_out_obj = self.registry('bots.stock.picking.out')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id
        location_dest_id = self.get_ref('stock', 'stock_location_customers')[1]
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKOUT_002',
                'partner_id': partner_id,
                'name': 'BT_PICKOUT_002',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'out',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 1,
                        'name': 'BT_PICKOUT_002/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_out_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.out', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Perform some invalid actions - should all fail
        with self.assertRaises(osv.except_osv):
            wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_cancel', self.cr)
        picking.refresh()
        self.assertNotEquals(picking.state, 'cancel', 'Picking should not be cancelled')

        with self.assertRaises(osv.except_osv):
            picking.cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.action_done()
        with self.assertRaises(osv.except_osv):
            picking.unlink()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_cancel()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_scrap(0, False)
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_done()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].unlink()

        # 4. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 5. Verify file results
        files = self._get_file_data('bots.stock.picking.out', '^picking_out_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'out'}],
              u'pickings': [{u'id': u'BTPICKOUT002',
                             u'line': [{u'id': u'BTPICKOUT002S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 1,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKOUT002',
                             u'order': u'BTPICKOUT002',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'out'}]}},
            'Output file has unexpected content')

        # 6. Temporarily disable cancelles and perform invalid actions again - should all fail
        self.backend_model.write(self.cr, self.uid, self.backend_id, {'feat_picking_out_cancel': 'reject'})
        wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_cancel', self.cr)
        picking.refresh()
        self.assertNotEquals(picking.state, 'cancel', 'Picking should not be cancelled')
        with self.assertRaises(osv.except_osv):
            picking.cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.action_done()
        with self.assertRaises(osv.except_osv):
            picking.unlink()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_cancel()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_scrap(0, False)
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_done()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].unlink()
        self.backend_model.write(self.cr, self.uid, self.backend_id, {'feat_picking_out_cancel': 'export'})

        # 7. Attempt to cancel picking
        wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_cancel', self.cr) # FIXME: Workflow breaking after the first cancel attempt? (Core bug?)
        picking.action_cancel()
        picking.refresh()
        self.assertEquals(picking.state, 'cancel', 'Picking should be cancelled')

        # 8. Get binder and job details
        bots_picking_id = bots_picking_out_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_cancel('bots.stock.picking.out', %d)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to cancel picking')

        # 9. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 10. Verify file results # FIXME: Old file not cleaned up corectly - leaving orphaned tmp file behind
        files = self._get_file_data('bots.stock.picking.out', '^picking_out_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'cancel',
                           u'type': u'out'}],
              u'pickings': [{u'id': u'BTPICKOUT002',
                             u'name': u'BTPICKOUT002',
                             u'order': u'BTPICKOUT002',
                             u'state': u'delete',
                             u'type': u'out'}]}},
            'Output file has unexpected content')

    def test_02_create_picking_and_get_reception(self):
        """ Create a new picking and test a full receipt """
        picking_obj = self.registry('stock.picking')
        bots_picking_out_obj = self.registry('bots.stock.picking.out')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id
        location_dest_id = self.get_ref('stock', 'stock_location_customers')[1]
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKOUT_003',
                'partner_id': partner_id,
                'name': 'BT_PICKOUT_003',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'out',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 5,
                        'name': 'BT_PICKOUT_003/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_out_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.out', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.out', '^picking_out_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'out'}],
              u'pickings': [{u'id': u'BTPICKOUT003',
                             u'line': [{u'id': u'BTPICKOUT003S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 5,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKOUT003',
                             u'order': u'BTPICKOUT003',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'out'}]}},
            'Output file has unexpected content')

        # 5. Simulate importing delivery with tracking but not shipped
        conf = [{
                'orderconf': {
                        'shipment': [{
                                'date_ship': '2014-01-01 00:00:00',
                                'confirmed': 'N',
                                'name': 'BTPICKOUT003',
                                'date_delivery': '2014-01-02 00:00:00',
                                'references': [{'type': 'shipping_ref', 'id': 'BTPICKOUT003_PASS'}, {'type': 'purchase_ref', 'id': 'BTPICKOUT003_FAIL'}],
                                'invoice': [{'currency': 'EUR', 'payment_term': 'C'}],
                                'partner': [],
                                'line': [{
                                        'product': 'M-Opt',
                                        'seq': "1",
                                        'qty_real': "5",
                                        'qty_expected': "5",
                                        'references': [],
                                        'type': 'out',
                                        'id': 'BTPICKOUT003S1',
                                    }],
                                'type': 'out',
                                'id': 'BTPICKOUT003',
                            }],
                            'header': [{
                                    "msg_id": "0",
                                    "msg_id2": "0",
                                    "test": "False",
                                    "type": "945 E",
                                    "state": "O",
                                }]
                    }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.out', 'picking_conf_%s.json', data)

        # 6. Create and run job to import confirmation
        self.backend_model._scheduler_import_stock_picking_out_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertEquals(picking.state, 'assigned', 'Picking should remain assigned')
        self.assertEquals(picking.carrier_tracking_ref, 'BTPICKOUT003_PASS', 'Picking should have a carrier reference')

        # 7. Simulate importing delivery with tracking and shipping

        conf[0]['orderconf']['shipment'][0]['confirmed'] = 'Y'
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.out', 'picking_conf_%s.json', data)

        # 8. Create and run job to import confirmation
        self.backend_model._scheduler_import_stock_picking_out_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertEquals(picking.state, 'done', 'Picking should remain assigned')

    def test_03_create_picking_and_get_part_reception(self):
        """ Create a new picking and test a partial followed by a remaining receipt """
        picking_obj = self.registry('stock.picking')
        bots_picking_out_obj = self.registry('bots.stock.picking.out')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id
        location_dest_id = self.get_ref('stock', 'stock_location_customers')[1]
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKOUT_004',
                'partner_id': partner_id,
                'name': 'BT_PICKOUT_004',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'out',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 5,
                        'name': 'BT_PICKOUT_004/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_out_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.out', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.out', '^picking_out_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'out'}],
              u'pickings': [{u'id': u'BTPICKOUT004',
                             u'line': [{u'id': u'BTPICKOUT004S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 5,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKOUT004',
                             u'order': u'BTPICKOUT004',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'out'}]}},
            'Output file has unexpected content')

        # 5. Simulate importing delivery with tracking and part shipped
        conf = [{
                'orderconf': {
                        'shipment': [{
                                'date_ship': '2014-01-01 00:00:00',
                                'confirmed': 'Y',
                                'name': 'BTPICKOUT004',
                                'date_delivery': '2014-01-02 00:00:00',
                                'references': [{'type': 'shipping_ref', 'id': 'BTPICKOUT004_PASS'}, {'type': 'purchase_ref', 'id': 'BTPICKOUT004_FAIL'}],
                                'invoice': [{'currency': 'EUR', 'payment_term': 'C'}],
                                'partner': [],
                                'line': [{
                                        'product': 'M-Opt',
                                        'seq': "1",
                                        'qty_real': "2",
                                        'qty_expected': "5",
                                        'references': [],
                                        'type': 'out',
                                        'id': 'BTPICKOUT004S1',
                                    }],
                                'type': 'out',
                                'id': 'BTPICKOUT004',
                            }],
                            'header': [{
                                    "msg_id": "0",
                                    "msg_id2": "0",
                                    "test": "False",
                                    "type": "945 E",
                                    "state": "O",
                                }]
                    }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.out', 'picking_conf_%s.json', data)

        # 6. Create and run job to import confirmation
        self.backend_model._scheduler_import_stock_picking_out_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertEquals(picking.state, 'assigned', 'Picking should remain assigned')
        self.assertEquals(picking.move_lines[0].product_qty, 3, 'Picking should only be confirmed for 3')
        self.assertEquals(picking.carrier_tracking_ref, '', 'Picking should not have a carrier reference')

        new_picking = picking.backorder_id
        self.assertNotEquals(new_picking.id, False, 'A backorder should exist for this picking')
        self.assertEquals(new_picking.state, 'done', 'Backorder picking should remain assigned')
        self.assertEquals(new_picking.move_lines[0].product_qty, 2, 'Backorder picking should only be confirmed for 2')
        self.assertEquals(new_picking.carrier_tracking_ref, 'BTPICKOUT004_PASS', 'Backorder picking should have a carrier reference')

        # 7. Simulate importing delivery with remaining stock
        conf[0]['orderconf']['shipment'][0]['line'][0]['qty_real'] = '3'
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.out', 'picking_conf_%s.json', data)

        # 8. Create and run job to import confirmation for remaining stock
        self.backend_model._scheduler_import_stock_picking_out_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertNotEquals(picking.backorder_id.id, False, 'A backorder should not exist for this picking')
        self.assertEquals(picking.state, 'done', 'Picking should remain assigned')
        self.assertEquals(picking.move_lines[0].product_qty, 3, 'Picking should only be confirmed for 3')
        self.assertEquals(picking.carrier_tracking_ref, 'BTPICKOUT004_PASS', 'Picking should have a carrier reference')

    def test_03_create_picking_and_get_invalid_reception(self):
        """ Create a new picking and test an invalid receipt """
        picking_obj = self.registry('stock.picking')
        bots_picking_out_obj = self.registry('bots.stock.picking.out')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = bots_warehouse.warehouse_id.lot_stock_id.id
        location_dest_id = self.get_ref('stock', 'stock_location_customers')[1]
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKOUT_005',
                'partner_id': partner_id,
                'name': 'BT_PICKOUT_005',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'out',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 5,
                        'name': 'BT_PICKOUT_005/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_out_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.out', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.out', '^picking_out_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'out'}],
              u'pickings': [{u'id': u'BTPICKOUT005',
                             u'line': [{u'id': u'BTPICKOUT005S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 5,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKOUT005',
                             u'order': u'BTPICKOUT005',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'out'}]}},
            'Output file has unexpected content')

        # 5. Simulate importing delivery with tracking and too much shipped (unsupported)
        conf = [{
                'orderconf': {
                        'shipment': [{
                                'date_ship': '2014-01-01 00:00:00',
                                'confirmed': 'Y',
                                'name': 'BTPICKOUT004',
                                'date_delivery': '2014-01-02 00:00:00',
                                'references': [{'type': 'shipping_ref', 'id': 'BTPICKOUT004_PASS'}, {'type': 'purchase_ref', 'id': 'BTPICKOUT004_FAIL'}],
                                'invoice': [{'currency': 'EUR', 'payment_term': 'C'}],
                                'partner': [],
                                'line': [{
                                        'product': 'M-Opt',
                                        'seq': "1",
                                        'qty_real': "10",
                                        'qty_expected': "5",
                                        'references': [],
                                        'type': 'out',
                                        'id': 'BTPICKOUT005S1',
                                    }],
                                'type': 'out',
                                'id': 'BTPICKOUT005',
                            }],
                            'header': [{
                                    "msg_id": "0",
                                    "msg_id2": "0",
                                    "test": "False",
                                    "type": "945 E",
                                    "state": "O",
                                }]
                    }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.out', 'picking_conf_%s.json', data)

        # 6. Create and run job to import confirmation - should fail
        self.backend_model._scheduler_import_stock_picking_out_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')

        with self.assertRaises(JobError):
            res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

class TestPickingIn(TestPicking):

    def test_00_create_picking(self):
        """ Create a new picking and test an export job is created on assignment """
        picking_obj = self.registry('stock.picking')
        bots_picking_in_obj = self.registry('bots.stock.picking.in')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = self.get_ref('stock', 'stock_location_suppliers')[1]
        location_dest_id = bots_warehouse.warehouse_id.lot_stock_id.id
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKIN_001',
                'partner_id': partner_id,
                'name': 'BT_PICKIN_001',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'in',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 1,
                        'name': 'BT_PICKIN_001/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_in_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.in', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.in', '^picking_in_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'in'}],
              u'pickings': [{u'id': u'BTPICKIN001',
                             u'line': [{u'id': u'BTPICKIN001S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 1,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKIN001',
                             u'order': u'BTPICKIN001',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'in'}]}},
            'Output file has unexpected content')

    def test_01_create_picking_and_cancel(self):
        """ Create a new picking and test an export job is created on assignment, then try to cancel before and after export """
        picking_obj = self.registry('stock.picking')
        bots_picking_in_obj = self.registry('bots.stock.picking.in')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = self.get_ref('stock', 'stock_location_suppliers')[1]
        location_dest_id = bots_warehouse.warehouse_id.lot_stock_id.id
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKIN_002',
                'partner_id': partner_id,
                'name': 'BT_PICKIN_002',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'in',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 1,
                        'name': 'BT_PICKIN_002/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_in_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.in', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Perform some invalid actions - should all fail
        with self.assertRaises(osv.except_osv):
            wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_cancel', self.cr)
        picking.refresh()
        self.assertNotEquals(picking.state, 'cancel', 'Picking should not be cancelled')

        with self.assertRaises(osv.except_osv):
            picking.cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.action_done()
        with self.assertRaises(osv.except_osv):
            picking.unlink()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_cancel()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_scrap(0, False)
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_done()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].unlink()

        # 4. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 5. Verify file results
        files = self._get_file_data('bots.stock.picking.in', '^picking_in_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'in'}],
              u'pickings': [{u'id': u'BTPICKIN002',
                             u'line': [{u'id': u'BTPICKIN002S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 1,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKIN002',
                             u'order': u'BTPICKIN002',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'in'}]}},
            'Output file has unexpected content')

        # 6. Temporarily disable cancelles and perform invalid actions again - should all fail
        self.backend_model.write(self.cr, self.uid, self.backend_id, {'feat_picking_in_cancel': 'reject'})
        wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_cancel', self.cr)
        picking.refresh()
        self.assertNotEquals(picking.state, 'cancel', 'Picking should not be cancelled')
        with self.assertRaises(osv.except_osv):
            picking.cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.action_done()
        with self.assertRaises(osv.except_osv):
            picking.unlink()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_cancel()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].cancel_assign()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_scrap(0, False)
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].action_done()
        with self.assertRaises(osv.except_osv):
            picking.move_lines[0].unlink()
        self.backend_model.write(self.cr, self.uid, self.backend_id, {'feat_picking_in_cancel': 'export'})

        # 7. Attempt to cancel picking
        wf_service.trg_validate(self.uid, 'stock.picking', picking.id, 'button_cancel', self.cr) # FIXME: Workflow breaking after the first cancel attempt? (Core bug?)
        picking.action_cancel()
        picking.refresh()
        self.assertEquals(picking.state, 'cancel', 'Picking should be cancelled')

        # 8. Get binder and job details
        bots_picking_id = bots_picking_in_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_cancel('bots.stock.picking.in', %d)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to cancel picking')

        # 9. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 10. Verify file results # FIXME: Old file not cleaned up corectly - leaving orphaned tmp file behind
        files = self._get_file_data('bots.stock.picking.in', '^picking_in_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'cancel',
                           u'type': u'in'}],
              u'pickings': [{u'id': u'BTPICKIN002',
                             u'name': u'BTPICKIN002',
                             u'order': u'BTPICKIN002',
                             u'state': u'delete',
                             u'type': u'in'}]}},
            'Output file has unexpected content')

    def test_02_create_picking_and_get_reception(self):
        """ Create a new picking and test a full receipt """
        picking_obj = self.registry('stock.picking')
        bots_picking_in_obj = self.registry('bots.stock.picking.in')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = self.get_ref('stock', 'stock_location_suppliers')[1]
        location_dest_id = bots_warehouse.warehouse_id.lot_stock_id.id
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKIN_003',
                'partner_id': partner_id,
                'name': 'BT_PICKIN_003',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'in',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 5,
                        'name': 'BT_PICKIN_003/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_in_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.in', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.in', '^picking_in_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'in'}],
              u'pickings': [{u'id': u'BTPICKIN003',
                             u'line': [{u'id': u'BTPICKIN003S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 5,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKIN003',
                             u'order': u'BTPICKIN003',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'in'}]}},
            'Output file has unexpected content')

        # 5. Simulate importing delivery with tracking but not shipped
        conf = [{
                'orderconf': {
                        'shipment': [{
                                'date_ship': '2014-01-01 00:00:00',
                                'confirmed': 'N',
                                'name': 'BTPICKIN003',
                                'date_delivery': '2014-01-02 00:00:00',
                                'references': [{'type': 'shipping_ref', 'id': 'BTPICKIN003_FAIL'}, {'type': 'purchase_ref', 'id': 'BTPICKIN003_PASS'}],
                                'invoice': [{'currency': 'EUR', 'payment_term': 'C'}],
                                'partner': [],
                                'line': [{
                                        'product': 'M-Opt',
                                        'seq': "1",
                                        'qty_real': "5",
                                        'qty_expected': "5",
                                        'references': [],
                                        'type': 'in',
                                        'id': 'BTPICKIN003S1',
                                    }],
                                'type': 'in',
                                'id': 'BTPICKIN003',
                            }],
                            'header': [{
                                    "msg_id": "0",
                                    "msg_id2": "0",
                                    "test": "False",
                                    "type": "945 E",
                                    "state": "O",
                                }]
                    }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.in', 'picking_conf_%s.json', data)

        # 6. Create and run job to import confirmation
        self.backend_model._scheduler_import_stock_picking_in_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertEquals(picking.state, 'assigned', 'Picking should remain assigned')
        self.assertEquals(picking.carrier_tracking_ref, 'BTPICKIN003_PASS', 'Picking should have a carrier reference')

        # 7. Simulate importing delivery with tracking and shipping

        conf[0]['orderconf']['shipment'][0]['confirmed'] = 'Y'
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.in', 'picking_conf_%s.json', data)

        # 8. Create and run job to import confirmation
        self.backend_model._scheduler_import_stock_picking_in_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertEquals(picking.state, 'done', 'Picking should remain assigned')

    def test_03_create_picking_and_get_part_reception(self):
        """ Create a new picking and test a partial followed by a remaining receipt """
        picking_obj = self.registry('stock.picking')
        bots_picking_in_obj = self.registry('bots.stock.picking.in')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = self.get_ref('stock', 'stock_location_suppliers')[1]
        location_dest_id = bots_warehouse.warehouse_id.lot_stock_id.id
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKIN_004',
                'partner_id': partner_id,
                'name': 'BT_PICKIN_004',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'in',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 5,
                        'name': 'BT_PICKIN_004/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_in_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.in', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.in', '^picking_in_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'in'}],
              u'pickings': [{u'id': u'BTPICKIN004',
                             u'line': [{u'id': u'BTPICKIN004S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 5,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKIN004',
                             u'order': u'BTPICKIN004',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'in'}]}},
            'Output file has unexpected content')

        # 5. Simulate importing delivery with tracking and part shipped
        conf = [{
                'orderconf': {
                        'shipment': [{
                                'date_ship': '2014-01-01 00:00:00',
                                'confirmed': 'Y',
                                'name': 'BTPICKIN004',
                                'date_delivery': '2014-01-02 00:00:00',
                                'references': [{'type': 'shipping_ref', 'id': 'BTPICKIN004_FAIL'}, {'type': 'purchase_ref', 'id': 'BTPICKIN004_PASS'}],
                                'invoice': [{'currency': 'EUR', 'payment_term': 'C'}],
                                'partner': [],
                                'line': [{
                                        'product': 'M-Opt',
                                        'seq': "1",
                                        'qty_real': "2",
                                        'qty_expected': "5",
                                        'references': [],
                                        'type': 'in',
                                        'id': 'BTPICKIN004S1',
                                    }],
                                'type': 'in',
                                'id': 'BTPICKIN004',
                            }],
                            'header': [{
                                    "msg_id": "0",
                                    "msg_id2": "0",
                                    "test": "False",
                                    "type": "945 E",
                                    "state": "O",
                                }]
                    }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.in', 'picking_conf_%s.json', data)

        # 6. Create and run job to import confirmation
        self.backend_model._scheduler_import_stock_picking_in_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertEquals(picking.state, 'assigned', 'Picking should remain assigned')
        self.assertEquals(picking.move_lines[0].product_qty, 3, 'Picking should only be confirmed for 3')
        self.assertEquals(picking.carrier_tracking_ref, '', 'Picking should not have a carrier reference')

        new_picking = picking.backorder_id
        self.assertNotEquals(new_picking.id, False, 'A backorder should exist for this picking')
        self.assertEquals(new_picking.state, 'done', 'Backorder picking should remain assigned')
        self.assertEquals(new_picking.move_lines[0].product_qty, 2, 'Backorder picking should only be confirmed for 2')
        self.assertEquals(new_picking.carrier_tracking_ref, 'BTPICKIN004_PASS', 'Backorder picking should have a carrier reference')

        # 7. Simulate importing delivery with remaining stock
        conf[0]['orderconf']['shipment'][0]['line'][0]['qty_real'] = '3'
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.in', 'picking_conf_%s.json', data)

        # 8. Create and run job to import confirmation for remaining stock
        self.backend_model._scheduler_import_stock_picking_in_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        picking.refresh()
        self.assertNotEquals(picking.backorder_id.id, False, 'A backorder should not exist for this picking')
        self.assertEquals(picking.state, 'done', 'Picking should remain assigned')
        self.assertEquals(picking.move_lines[0].product_qty, 3, 'Picking should only be confirmed for 3')
        self.assertEquals(picking.carrier_tracking_ref, 'BTPICKIN004_PASS', 'Picking should have a carrier reference')

    def test_03_create_picking_and_get_invalid_reception(self):
        """ Create a new picking and test an invalid receipt """
        picking_obj = self.registry('stock.picking')
        bots_picking_in_obj = self.registry('bots.stock.picking.in')
        job_obj = self.registry('queue.job')

        bots_warehouse = self.registry('bots.warehouse').browse(self.cr, self.uid, self.bots_warehouse_id)
        location_id = self.get_ref('stock', 'stock_location_suppliers')[1]
        location_dest_id = bots_warehouse.warehouse_id.lot_stock_id.id
        partner_id = self.get_ref('stock', 'res_partner_company_2')[1]
        product_id = self.get_ref('product', 'product_template_10')[1]
        uom_id = self.get_ref('product', 'product_uom_unit')[1]

        wf_service = netsvc.LocalService("workflow")

        # 1. Create and Asssign Picking
        picking_dict = {
                'origin': 'BT_PICKIN_005',
                'partner_id': partner_id,
                'name': 'BT_PICKIN_005',
                'company_id': bots_warehouse.warehouse_id.company_id.id,
                'type': 'in',
                'move_lines': [[0, False, {
                        'product_id': product_id,
                        'product_uom': uom_id,
                        'partner_id': partner_id,
                        'product_qty': 5,
                        'name': 'BT_PICKIN_005/1',
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'company_id': bots_warehouse.warehouse_id.company_id.id,
                    }]],
            }
        picking = self._create_and_assign_picking(picking_dict)
        self.assertEquals(picking.state, 'assigned', 'Picking was force assigned, should be assigned.')

        # 2. Get binder and job details
        bots_picking_id = bots_picking_in_obj.search(self.cr, self.uid, [('backend_id', '=', self.backend_id), ('openerp_id', '=', picking.id)])
        self.assertEquals(len(bots_picking_id), 1, 'One binder entry should be created to export picking')
        job_string = "openerp.addons.connector_bots.stock.export_picking_available('bots.stock.picking.in', %dL)" % (bots_picking_id[0],)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to export picking')

        # 3. Run export job
        res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])

        # 4. Verify file results
        files = self._get_file_data('bots.stock.picking.in', '^picking_in_.*\.json$')
        self.assertEquals(len(files.keys()), 1, 'One output file should be created for the picking export')
        data = json.loads(files.values()[0])
        del data['picking']['header'][0]['date_msg']
        del data['picking']['pickings'][0]['date']

        partner = self.registry('res.partner').browse(self.cr, self.uid, partner_id)
        self.assertEquals(data, {u'picking': {u'header': [{u'message_id': u'0',
                           u'partner_from': u'Bots Test',
                           u'partner_to': u'OpenERP Test',
                           u'state': u'done',
                           u'type': u'in'}],
              u'pickings': [{u'id': u'BTPICKIN005',
                             u'line': [{u'id': u'BTPICKIN005S1',
                                        u'price_currency': u'EUR',
                                        u'price_unit': 12.5,
                                        u'product': u'M-Opt',
                                        u'product_qty': 5,
                                        u'product_uos_qty': 0,
                                        u'seq': 1,
                                        u'uom': u'Unit(s)',
                                        u'uos': None}],
                             u'name': u'BTPICKIN005',
                             u'order': u'BTPICKIN005',
                             u'partner': {u'city': partner.city or False,
                                          u'country': partner.country_id and partner.country_id.code or False,
                                          u'email': partner.email or False,
                                          u'fax': partner.fax or False,
                                          u'id': 'P%d' % (partner.id),
                                          u'language': partner.lang or 'en_US',
                                          u'name': partner.name or False,
                                          u'phone': partner.phone or False,
                                          u'state': partner.state_id and partner.state_id.name or '',
                                          u'street1': partner.street or False,
                                          u'street2': partner.street2 or False,
                                          u'zip': partner.zip or False,},
                             u'state': u'new',
                             u'type': u'in'}]}},
            'Output file has unexpected content')

        # 5. Simulate importing delivery with tracking and too much shipped (unsupported)
        conf = [{
                'orderconf': {
                        'shipment': [{
                                'date_ship': '2014-01-01 00:00:00',
                                'confirmed': 'Y',
                                'name': 'BTPICKIN004',
                                'date_delivery': '2014-01-02 00:00:00',
                                'references': [{'type': 'shipping_ref', 'id': 'BTPICKIN004_FAIL'}, {'type': 'purchase_ref', 'id': 'BTPICKIN004_PASS'}],
                                'invoice': [{'currency': 'EUR', 'payment_term': 'C'}],
                                'partner': [],
                                'line': [{
                                        'product': 'M-Opt',
                                        'seq': "1",
                                        'qty_real': "10",
                                        'qty_expected': "5",
                                        'references': [],
                                        'type': 'in',
                                        'id': 'BTPICKIN005S1',
                                    }],
                                'type': 'in',
                                'id': 'BTPICKIN005',
                            }],
                            'header': [{
                                    "msg_id": "0",
                                    "msg_id2": "0",
                                    "test": "False",
                                    "type": "945 E",
                                    "state": "O",
                                }]
                    }
            }]
        data = json.dumps(conf)
        self._set_file_data('bots.stock.picking.in', 'picking_conf_%s.json', data)

        # 6. Create and run job to import confirmation - should fail
        self.backend_model._scheduler_import_stock_picking_in_conf(self.cr, self.uid, new_cr=False)
        job_string = "openerp.addons.connector_bots.stock_warehouse.import_picking_confirmation('bots.warehouse', %s, ['in', 'out'], new_cr=False)" % (bots_warehouse.id,)
        job_ids = job_obj.search(self.cr, self.uid, [('func_string', '=', job_string)])
        self.assertEquals(len(job_ids), 1, 'One job should be created to import picking confirmations')

        with self.assertRaises(JobError):
            res = self._run_job(job_ids[0])
        job_obj.unlink(self.cr, self.uid, [job_ids[0],])
